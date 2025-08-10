import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from uv_bump.main import (
    UVSyncError,
    _update_pyproject_contents,
    run_uv_sync,
    upgrade,
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
        upgrade(pyproject_file)

    mock.assert_called_once()

    result = tomllib.loads(pyproject_file.read_text())
    assert result["project"]["dependencies"] == ["polars>=1.21.0,<1.22"]


def test_upgrade_uv_sync_exception() -> None:
    with pytest.raises(UVSyncError) as error:  # noqa: PT012, SIM117
        with patch(upgrade.__module__ + ".subprocess.run") as mock:

            def run(*args, **kwargs) -> None:  # type:ignore[no-untyped-def] #noqa: ANN002, ANN003, ARG001
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="", stderr="uv sync error here"
                )

            mock.side_effect = run
            upgrade()

    assert str(error.value) == "UVSyncError(exit_code=1, message=\nuv sync error here)"


def test_update_with_upper_bound() -> None:
    content = """
        "polars>=1.20.0,<1.22",
    """
    result = _update_pyproject_contents(content, {"polars": "1.21.0"})
    assert '"polars>=1.21.0,<1.22"' in result


def test_update_extras() -> None:
    content = """
        "polars[sql]>=1.20",
    """
    assert '"polars[sql]>=1.21.0"' in _update_pyproject_contents(
        content,
        {"polars": "1.21.0"},
    )


def test_update_no_equals_sign() -> None:
    # this should not happen to start with, but good to check we only modify parts where
    # we expect an upgrade to be possible
    content = """
       "polars==1.20.0",
    """
    assert '"polars==1.20.0"' in _update_pyproject_contents(
        content,
        {"polars": "1.21.0"},
    )


def test_update_keep_comment() -> None:
    content = """
        "polars>=1.20.0",  # 1.21 has a bug
    """
    assert '"polars>=1.21.0",  # 1.21 has a bug' in _update_pyproject_contents(
        content,
        {"polars": "1.21.0"},
    )
