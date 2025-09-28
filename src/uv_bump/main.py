from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]  # pragma: no cover


class UVSyncError(Exception):  # noqa: D101
    exit_code: int
    msg: str

    def __init__(self, exit_code: int, msg: str) -> None:  # noqa: D107
        self.exit_code = exit_code
        self.msg = msg

    def __str__(self) -> str:  # noqa: D105
        return f"UVSyncError(exit_code={self.exit_code}, message=\n" + self.msg + ")"


def upgrade(pyproject_toml_file: Path | None = None) -> None:
    """Upgrade minimum versions of dependencies in specified pyproject.toml."""
    if pyproject_toml_file is None:
        pyproject_toml_file = Path("pyproject.toml")

    run_uv_sync()
    package_versions = collect_package_versions_from_lock_file(pyproject_toml_file)
    update_pyproject_toml(pyproject_toml_file, package_versions)


def run_uv_sync() -> None:
    """
    Find package upgrades through uv sync.

    Raises UVSyncError.
    """
    try:
        subprocess.run(
            ["uv", "sync", "--upgrade", "--all-extras"],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise UVSyncError(error.returncode, error.stderr) from error


def collect_package_versions_from_lock_file(
    pyproject_toml_file: Path,
) -> dict[str, str]:
    """
    Gather all dependency versions.

    Args:
        pyproject_toml_file: path of the pyproject.toml file

    Returns:
        dict with the package name as key and package version as value

    """
    lock_path = pyproject_toml_file.parent / "uv.lock"
    contents = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return {p["name"]: p["version"] for p in contents["package"] if "version" in p}


def update_pyproject_toml(file: Path, package_versions: dict[str, str]) -> None:
    """
    Update specified pyproject.toml file with minimum version bounds (>=, ~=).

    Params:
         file: the path to the pyproject.toml file
         package_version_updated: dict of package names and package versions.
    """
    contents = file.read_text(encoding="utf-8")
    contents_updated = _update_pyproject_contents(contents, package_versions)
    file.write_text(contents_updated, encoding="utf-8")


def _update_pyproject_contents(
    contents: str, package_version_updated: dict[str, str]
) -> str:
    for package, version in package_version_updated.items():
        contents = _replace_package_version(contents, package, version)
    return contents


def _replace_package_version(text: str, package: str, version: str) -> str:
    # we assume the following:
    # 1. the package name is directly preceded by a double quote
    # 2. (?:\[[^\]]*\])? => after the package name there can be extras, if so, we
    #    require it to be in square brackets
    # 3. (>|>=|~=) there will be a version specifier that allows updating
    # 4. [^"`,;]+' =>  we need to stop. There can be more version specifiers, separated
    #    by comma, and/or system specifiers (separated by semicolon), or none, in which
    #    case we encounter the double quotes.
    pattern = r'"(' + package + r'(?:\[[^\]]*\])?)(>|>=|~=)[^"`,;]+'
    replacement = r'"\1>=' + version

    text, _ = re.subn(pattern, replacement, text)
    return text
