import argparse
from pathlib import Path
from unittest.mock import patch

from uv_bump.cli import cli, parse_args


def test_cli() -> None:
    with (
        patch("uv_bump.cli.parse_args") as mock_parse_args,
        patch("uv_bump.cli.bump_pyproject") as mock_bump,
    ):
        mock_parse_args.return_value = argparse.Namespace(
            pyproject_toml="hello",
            verbose=False,
            upgrade=True,
            update_unconstrained=False,
        )
        cli()

    mock_bump.assert_called_once_with(
        Path("hello"), verbose=False, upgrade=True, update_unconstrained=False
    )


def test_cli_no_upgrade() -> None:
    with (
        patch("uv_bump.cli.parse_args") as mock_parse_args,
        patch("uv_bump.cli.bump_pyproject") as mock_bump,
    ):
        mock_parse_args.return_value = argparse.Namespace(
            pyproject_toml="hello",
            verbose=False,
            upgrade=False,
            update_unconstrained=False,
        )
        cli()

    mock_bump.assert_called_once_with(
        Path("hello"), verbose=False, upgrade=False, update_unconstrained=False
    )


def test_parse_args() -> None:
    result = parse_args(["--pyproject-toml", "world"])

    assert result == argparse.Namespace(
        pyproject_toml="world", verbose=False, upgrade=True, update_unconstrained=False
    )


def test_parse_args_no_upgrade() -> None:
    result = parse_args(["--pyproject-toml", "world", "--no-upgrade"])

    assert result == argparse.Namespace(
        pyproject_toml="world", verbose=False, upgrade=False, update_unconstrained=False
    )


def test_parse_args_update_unconstrained() -> None:
    result = parse_args(["--update-unconstrained"])

    assert result == argparse.Namespace(
        pyproject_toml=None,
        verbose=False,
        upgrade=True,
        update_unconstrained=True,
    )


def test_cli_update_unconstrained() -> None:
    with (
        patch("uv_bump.cli.parse_args") as mock_parse_args,
        patch("uv_bump.cli.bump_pyproject") as mock_bump,
    ):
        mock_parse_args.return_value = argparse.Namespace(
            pyproject_toml=None,
            verbose=False,
            upgrade=True,
            update_unconstrained=True,
        )
        cli()

    mock_bump.assert_called_once_with(
        None,
        verbose=False,
        upgrade=True,
        update_unconstrained=True,
    )
