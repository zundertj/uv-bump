from unittest.mock import patch

from uv_bump.main import _update_pyproject_contents, collect_uv_updates


def test_collect_uv_updates() -> None:
    with patch(collect_uv_updates.__module__ + ".subprocess.run") as mock:
        mock.return_value.stderr = "Upgrade\n + polars==1.20.0\n - polars==1.19.0"
        assert collect_uv_updates() == {"polars": "1.20.0"}


def test_update_with_upper_bound() -> None:
    content = """"[project]
name = "uv-bump"
version = "0.1.0"
description = "Bump pyproject.toml dependency minimum versions."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "polars>=1.20.0,<1.22",
]"""

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
