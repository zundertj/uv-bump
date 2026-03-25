import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from uv_bump.main import (
    UVSyncError,
    _update_pyproject_contents,
    bump_pyproject,
    collect_all_pyproject_files,
    run_uv_sync,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-untyped]  # pragma: no cover


@pytest.fixture
def lock_file_contents() -> str:
    return """[[package]]
name = "uv-bump"
version = "0.1.2"

[[package]]
name = "polars"
version = "1.21.0"
    """


@pytest.fixture
def pyproject_toml_contents() -> str:
    return """[project]
name = "uv-bump"
version = "0.1.2"
description = "Bump pyproject.toml dependency minimum versions."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "polars>=1.20.0,<1.22",
]"""


def test_upgrade(
    tmp_path: Path, lock_file_contents: str, pyproject_toml_contents: str
) -> None:
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text(lock_file_contents)  # contents after uv-sync run

    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_toml_contents)

    with patch(run_uv_sync.__module__ + ".subprocess.run") as mock:
        bump_pyproject(pyproject_file, verbose=True)

    mock.assert_called_once()

    result = tomllib.loads(pyproject_file.read_text())
    assert result["project"]["dependencies"] == ["polars>=1.21.0,<1.22"]


def test_collect_all_pyproject_files() -> None:
    resource_dir = Path(__file__).parent / "resources"
    lock_file = resource_dir / "uv_workspaces.lock"
    result = collect_all_pyproject_files(lock_file)
    assert len(result) == 2  # noqa: PLR2004
    assert resource_dir / "pyproject.toml" in result
    assert resource_dir / "packages/my_lib/pyproject.toml" in result


def test_collect_all_pyproject_files_manifest_without_members(tmp_path: Path) -> None:
    """Test manifest without members returns single pyproject.toml, not KeyError."""
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("""version = 1
requires-python = ">=3.11"

[manifest]
overrides = [{ name = "django", specifier = ">=6.0.1" }]

[[package]]
name = "my-project"
version = "0.1.0"
source = { virtual = "." }
""")
    result = collect_all_pyproject_files(lock_file)
    assert result == [tmp_path / "pyproject.toml"]


def test_bump_without_upgrade_uv_sync() -> None:
    with patch(bump_pyproject.__module__ + ".subprocess.run") as mock:
        bump_pyproject(upgrade=False)
    assert "--upgrade" not in mock.call_args[0][0]


def test_bump_with_upgrade_uv_sync() -> None:
    with patch(bump_pyproject.__module__ + ".subprocess.run") as mock:
        bump_pyproject(upgrade=True)
    assert "--upgrade" in mock.call_args[0][0]


def test_upgrade_uv_sync_exception() -> None:
    with pytest.raises(UVSyncError) as error:  # noqa: PT012, SIM117
        with patch(bump_pyproject.__module__ + ".subprocess.run") as mock:

            def run(*args, **kwargs) -> None:  # type:ignore[no-untyped-def] #noqa: ANN002, ANN003, ARG001
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="", stderr="uv sync error here"
                )

            mock.side_effect = run
            bump_pyproject()

    assert str(error.value) == "UVSyncError(exit_code=1, message=\nuv sync error here)"


def test_update_with_upper_bound() -> None:
    content = """
        "polars>=1.20.0,<1.22",
    """
    result, _, _ = _update_pyproject_contents(content, {"polars": "1.21.0"})
    assert '"polars>=1.21.0,<1.22"' in result


def test_update_extras() -> None:
    content = """
        "polars[sql]>=1.20",
    """
    assert (
        '"polars[sql]>=1.21.0"'
        in _update_pyproject_contents(
            content,
            {"polars": "1.21.0"},
        )[0]
    )


def test_update_no_equals_sign() -> None:
    # this should not happen to start with, but good to check we only modify parts where
    # we expect an upgrade to be possible
    content = """
       "polars==1.20.0",
    """
    result, packages_updated, _ = _update_pyproject_contents(
        content,
        {"polars": "1.21.0"},
    )
    assert '"polars==1.20.0"' in result
    assert packages_updated == []


def test_update_keep_comment() -> None:
    content = """
        "polars>=1.20.0",  # 1.21 has a bug
    """
    result, packages_updated, _ = _update_pyproject_contents(
        content,
        {"polars": "1.21.0"},
    )

    assert '"polars>=1.21.0",  # 1.21 has a bug' in result
    assert packages_updated == ["polars"]


def test_upgrade_verbose_shows_correct_before_after_versions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Lock file content before uv sync
    lock_before = """[[package]]
name = "uv-bump"
version = "0.1.2"

[[package]]
name = "polars"
version = "1.20.0"
"""
    # Lock file content after uv sync (updated version)
    lock_after = """[[package]]
name = "uv-bump"
version = "0.1.2"

[[package]]
name = "polars"
version = "1.21.0"
"""
    pyproject_content = """[project]
name = "uv-bump"
version = "0.1.2"
description = "Bump pyproject.toml dependency minimum versions."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "polars>=1.20.0,<1.22",
]"""

    lock_file = tmp_path / "uv.lock"
    lock_file.write_text(lock_before)

    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)

    # Mock run_uv_sync to write updated lock file
    with patch(run_uv_sync.__module__ + ".run_uv_sync") as mock_run_uv_sync:

        def mock_sync(*, upgrade: bool) -> None:  # noqa: ARG001
            lock_file.write_text(lock_after)

        mock_run_uv_sync.side_effect = mock_sync

        bump_pyproject(pyproject_file, verbose=True)
        mock_run_uv_sync.assert_called_once()

    # Capture verbose output
    captured = capsys.readouterr()
    output = captured.out

    assert "\tpolars\t\t1.20.0 → 1.21.0" in output, (
        f"Expected version change not found in output:\n{output}"
    )


def test_upgrade_verbose_shows_correct_before_after_from_pyproject_bug(
    tmp_path: Path,
    lock_file_contents: str,
    pyproject_toml_contents: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text(lock_file_contents)  # lock already has 1.21.0

    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_toml_contents)

    with patch(run_uv_sync.__module__ + ".subprocess.run") as mock:
        bump_pyproject(pyproject_file, verbose=True)

    mock.assert_called_once()

    captured = capsys.readouterr()
    output = captured.out

    assert "\tpolars\t\t-\t\t1.20.0 → 1.21.0" in output, (
        f"Expected version change not found in output:\n{output}"
    )
