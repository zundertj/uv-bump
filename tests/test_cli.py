import argparse
from pathlib import Path
from unittest.mock import patch

from uv_bump.cli import cli, parse_args


def test_cli() -> None:
    with patch("uv_bump.cli.parse_args") as mock_parse_args:  # noqa: SIM117
        with patch("uv_bump.cli.upgrade") as mock_upgrade:
            mock_parse_args.return_value = argparse.Namespace(pyproject_toml="hello")
            cli()

    mock_upgrade.assert_called_once_with(Path("hello"))


def test_parse_args() -> None:
    result = parse_args(["--pyproject-toml", "world"])

    assert result == argparse.Namespace(pyproject_toml="world")
