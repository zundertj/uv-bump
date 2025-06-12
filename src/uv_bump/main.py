from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]

UV_SYNC_UPGRADE_MARKER = (
    " + "  # uv sync emits upgraded versions on lines starting with this marker
)


def upgrade(pyproject_toml_file: Path | None = None) -> None:
    """Upgrade minimum versions of dependencies in specified pyproject.toml."""
    if pyproject_toml_file is None:
        pyproject_toml_file = Path("pyproject.toml")
    package_version_updated = collect_uv_updates(pyproject_toml_file)
    update_pyproject_toml(pyproject_toml_file, package_version_updated)


def collect_uv_updates(pyproject_toml_file: Path) -> dict[str, str]:
    """
    Find package upgrades through uv sync.

    Args:
        pyproject_toml_file: Path to the pyproject.toml file to analyze

    Returns:
        dict with the package name as key and package version as value

    """
    package_version_updated: dict[str, str] = {}

    # First, collect updates for regular dependencies
    result = subprocess.run(  # noqa: S603
        ["uv", "sync", "--upgrade"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    _process_uv_output(result.stderr, package_version_updated)

    # Then, collect updates for each optional dependency group
    optional_groups = _get_optional_dependency_groups(pyproject_toml_file)
    for group in optional_groups:
        try:
            result = subprocess.run(  # noqa: S603
                ["uv", "sync", "--upgrade", "--extra", group],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
            )
            _process_uv_output(result.stderr, package_version_updated)
        except subprocess.CalledProcessError:  # noqa: PERF203
            # Skip optional groups that fail to sync
            continue

    return package_version_updated


def _process_uv_output(stderr: str, package_version_updated: dict[str, str]) -> None:
    """Process uv sync stderr output to extract package updates."""
    lines = stderr.splitlines()
    for line in lines:
        if line.startswith(UV_SYNC_UPGRADE_MARKER):
            pkg, version = line[len(UV_SYNC_UPGRADE_MARKER) :].split("==")
            package_version_updated[pkg.strip()] = version.strip()


def _get_optional_dependency_groups(pyproject_toml_file: Path) -> list[str]:
    """Extract optional dependency group names from pyproject.toml."""
    try:
        with pyproject_toml_file.open("rb") as f:
            data = tomllib.load(f)

        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        return list(optional_deps.keys())
    except (OSError, tomllib.TOMLDecodeError):
        # If we can't parse the file, return empty list
        return []


def update_pyproject_toml(file: Path, package_version_updated: dict[str, str]) -> None:
    """
    Update specified pyproject.toml file with minimum versions (>=).

    Params:
         file: the path to the pyproject.toml file
         package_version_updated: dict of package names and package versions.
    """
    contents = file.read_text(encoding="utf-8")
    contents = _update_pyproject_contents(contents, package_version_updated)
    file.write_text(contents, encoding="utf-8")


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

    text, num_replacements = re.subn(pattern, replacement, text)
    return text
