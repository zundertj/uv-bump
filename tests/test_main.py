from unittest.mock import MagicMock, patch

from uv_bump.main import (
    _get_optional_dependency_groups,
    _update_pyproject_contents,
    collect_uv_updates,
)


def test_collect_uv_updates() -> None:
    mock_file = MagicMock()
    mock_file.open.return_value.__enter__.return_value = (
        b"[project]\n[project.optional-dependencies]\ntest = []"
    )

    module = collect_uv_updates.__module__
    with patch(module + ".subprocess.run") as mock_subprocess, \
         patch(module + "._get_optional_dependency_groups") as mock_groups:
        stderr = "Upgrade\n + polars==1.20.0\n - polars==1.19.0"
        mock_subprocess.return_value.stderr = stderr
        mock_groups.return_value = []
        assert collect_uv_updates(mock_file) == {"polars": "1.20.0"}


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


def test_get_optional_dependency_groups() -> None:
    """Test parsing optional dependency groups from pyproject.toml."""
    content = b"""[project]
name = "test"
[project.optional-dependencies]
dev = ["pytest"]
test = ["coverage"]
docs = ["sphinx"]
"""
    mock_file = MagicMock()
    mock_file.open.return_value.__enter__.return_value = content

    with patch("uv_bump.main.tomllib.load") as mock_load:
        mock_load.return_value = {
            "project": {
                "optional-dependencies": {
                    "dev": ["pytest"],
                    "test": ["coverage"],
                    "docs": ["sphinx"]
                }
            }
        }
        groups = _get_optional_dependency_groups(mock_file)
        assert set(groups) == {"dev", "test", "docs"}


def test_collect_uv_updates_with_optional_dependencies() -> None:
    """Test that collect_uv_updates handles optional dependencies."""
    mock_file = MagicMock()

    module = collect_uv_updates.__module__
    with patch(module + ".subprocess.run") as mock_subprocess, \
         patch(module + "._get_optional_dependency_groups") as mock_groups:

        # Mock subprocess calls: first for regular deps, then for optional deps
        mock_subprocess.side_effect = [
            # Regular dependencies
            MagicMock(stderr="Upgrade\n + polars==1.20.0\n - polars==1.19.0"),
            # Optional dependency group "dev"
            MagicMock(stderr="Upgrade\n + pytest==8.0.0\n - pytest==7.4.0"),
            # Optional dependency group "test"
            MagicMock(stderr="Upgrade\n + coverage==7.4.0\n - coverage==7.3.0"),
        ]
        mock_groups.return_value = ["dev", "test"]

        result = collect_uv_updates(mock_file)
        expected = {"polars": "1.20.0", "pytest": "8.0.0", "coverage": "7.4.0"}
        assert result == expected

        # Verify correct subprocess calls were made
        expected_call_count = 3
        assert mock_subprocess.call_count == expected_call_count
        calls = mock_subprocess.call_args_list

        # First call: regular dependencies
        assert calls[0][0][0] == ["uv", "sync", "--upgrade"]

        # Second call: dev optional dependencies
        assert calls[1][0][0] == ["uv", "sync", "--upgrade", "--extra", "dev"]

        # Third call: test optional dependencies
        assert calls[2][0][0] == ["uv", "sync", "--upgrade", "--extra", "test"]


def test_get_optional_dependency_groups_empty() -> None:
    """Test handling when no optional dependencies exist."""
    mock_file = MagicMock()

    with patch("uv_bump.main.tomllib.load") as mock_load:
        mock_load.return_value = {"project": {}}
        groups = _get_optional_dependency_groups(mock_file)
        assert groups == []


def test_get_optional_dependency_groups_parse_error() -> None:
    """Test handling when TOML parsing fails."""
    import tomllib
    mock_file = MagicMock()

    with patch("uv_bump.main.tomllib.load") as mock_load:
        mock_load.side_effect = tomllib.TOMLDecodeError("Parse error", "", 0)
        groups = _get_optional_dependency_groups(mock_file)
        assert groups == []
