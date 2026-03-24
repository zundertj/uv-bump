from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]  # pragma: no cover

LOCK_FILE_NAME = "uv.lock"
PYPROJECT_FILE_NAME = "pyproject.toml"


class UVSyncError(Exception):  # noqa: D101
    exit_code: int
    msg: str

    def __init__(self, exit_code: int, msg: str) -> None:  # noqa: D107
        self.exit_code = exit_code
        self.msg = msg

    def __str__(self) -> str:  # noqa: D105
        return f"UVSyncError(exit_code={self.exit_code}, message=\n" + self.msg + ")"


def _print_changes_table(
        before_versions: dict[str, str],
        packages_updated: list[str],
        lock_before: dict[str, str],
        lock_after: dict[str, str],
) -> None:
    """Print a table showing lock file changes and pyproject.toml changes."""
    print("\tPackage\t\tLock file\t\tpyproject.toml")  # noqa: T201

    for pkg in packages_updated:
        lock_b, lock_a = lock_before.get(pkg, "?"), lock_after.get(pkg, "?")
        pyproject_b = before_versions.get(pkg, "?")

        lock_str = f"{lock_b} → {lock_a}" if lock_b != lock_a else "-"
        pyproject_str = f"{pyproject_b} → {lock_a}"

        print(f"\t{pkg}\t\t{lock_str}\t\t{pyproject_str}")  # noqa: T201

    if not packages_updated:
        print("\tNo packages updated")  # noqa: T201


def bump_pyproject(
        root_pyproject_toml_file: Path | None = None, *, verbose: bool = False, upgrade: bool = False,
) -> None:
    """
    Upgrade minimum versions of dependencies in specified pyproject.toml.

    Params:
        root_pyproject_toml_file: main pyproject.toml file. If using workspaces, should
                                  be the root one.
        verbose: report per pyproject.toml file the package version changes made.
        upgrade: run --upgrade as part of the uv sync
    """
    if root_pyproject_toml_file is None:
        root_pyproject_toml_file = Path(PYPROJECT_FILE_NAME)

    lock_path = root_pyproject_toml_file.parent / LOCK_FILE_NAME

    lock_before = collect_package_versions_from_lock_file(lock_path)

    run_uv_sync(upgrade)

    lock_after = collect_package_versions_from_lock_file(lock_path)

    pyproject_files = collect_all_pyproject_files(lock_path)
    for pyproject_file in pyproject_files:
        packages_updated, before_versions = update_pyproject_toml(
            pyproject_file, lock_after
        )

        if verbose:
            print(f"Processed {pyproject_file}")  # noqa: T201
            _print_changes_table(
                before_versions,
                packages_updated,
                lock_before,
                lock_after,
            )


def run_uv_sync(upgrade: bool) -> None:
    """
    Find package upgrades through uv sync.

    Params:
        upgrade: run --upgrade as part of the uv sync

    Raises UVSyncError.
    """
    args = ["uv", "sync", "--all-extras"]
    if upgrade:
        args.append("--upgrade")
    try:
        subprocess.run(
            args,  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise UVSyncError(error.returncode, error.stderr) from error


def collect_package_versions_from_lock_file(lock_path: Path) -> dict[str, str]:
    """
    Gather all dependency versions.

    Args:
        lock_path: path to uv.lock file

    Returns:
        dict with the package name as key and package version as value

    """
    contents = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return {p["name"]: p["version"] for p in contents["package"] if "version" in p}


def collect_all_pyproject_files(lock_path: Path) -> list[Path]:
    """
    Determine all pyproject.toml file locations in the project from uv.lock file.

    Args:
        lock_path: the full path to the lock file

    Returns:
        list of paths to pyproject.toml files

    """
    contents = tomllib.loads(lock_path.read_text(encoding="utf-8"))

    if "manifest" in contents and "members" in contents["manifest"]:
        # workspaces
        member_paths = []

        for member in contents["manifest"]["members"]:
            for pkg in contents["package"]:
                if pkg["name"] == member:
                    source = pkg["source"]
                    for source_type in ["editable", "virtual"]:
                        if source_type in source:
                            member_paths.append(
                                lock_path.parent
                                / source[source_type]
                                / PYPROJECT_FILE_NAME
                            )
                            continue

        return member_paths

    return [lock_path.parent / PYPROJECT_FILE_NAME]


def update_pyproject_toml(
        file: Path, package_versions: dict[str, str]
) -> tuple[list[str], dict[str, str]]:
    """
    Update specified pyproject.toml file with minimum version bounds (>=, ~=).

    Params:
        file: the path to the pyproject.toml file
        package_versions: dict of package names and package versions.

    Returns:
        tuple of (list of packages updated, dict mapping package to before version)

    """
    contents = file.read_text(encoding="utf-8")
    contents_updated, packages_updated, before_versions = _update_pyproject_contents(
        contents, package_versions
    )
    file.write_text(contents_updated, encoding="utf-8")
    return packages_updated, before_versions


def _update_pyproject_contents(
        contents: str, package_version_updated: dict[str, str]
) -> tuple[str, list[str], dict[str, str]]:
    package_updates = []
    before_versions = {}
    for package, version in package_version_updated.items():
        contents, count, before_version = _replace_package_version(
            contents, package, version
        )
        if count > 0:
            package_updates.append(package)
            if before_version is not None:
                before_versions[package] = before_version
    return contents, package_updates, before_versions


def _replace_package_version(
        text: str, package: str, version: str
) -> tuple[str, int, str | None]:
    # we assume the following:
    # 1. the package name is directly preceded by a double quote
    # 2. (?:\[[^\]]*\])? => after the package name there can be extras, if so, we
    #    require it to be in square brackets
    # 3. (>=|~=|>) there will be a version specifier that allows updating
    # 4. [^"`,;]+' =>  we need to stop. There can be more version specifiers, separated
    #    by comma, and/or system specifiers (separated by semicolon), or none, in which
    #    case we encounter the double quotes.
    escaped_package = re.escape(package)
    pattern = r'"(' + escaped_package + r'(?:\[[^\]]*\])?)\s*(>=|~=|>)\s*([^"`,;]+)'
    replacement = r'"\1>=' + version

    # Find first match to capture before version
    match = re.search(pattern, text)
    before_version = match.group(3).strip() if match else None

    text_updated = re.sub(pattern, replacement, text)

    # we count the number of lines changed, rather than using re.subn, as re.subn still
    # reports changes due to the dynamic pattern
    num_lines_changes = sum(
        s1 != s2
        for s1, s2 in zip(text.splitlines(), text_updated.splitlines(), strict=True)
    )

    return text_updated, num_lines_changes, before_version
