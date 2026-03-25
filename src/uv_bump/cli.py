import argparse
import importlib.metadata
import sys
from collections.abc import Sequence
from pathlib import Path

from uv_bump.main import bump_pyproject

PROG = "uv-bump"


def cli() -> None:
    args = parse_args(sys.argv[1:])
    bump_pyproject(
        Path(args.pyproject_toml) if args.pyproject_toml is not None else None,
        verbose=args.verbose,
        upgrade=args.upgrade,
    )


def parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "UV-bump updates your pyproject.toml minimum versions to the latest"
            " feasible version"
        ),
    )

    parser.add_argument(
        "--pyproject-toml",
        help="File to update",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Report changes made"
    )
    parser.add_argument(
        "-n",
        "--no-upgrade",
        action="store_false",
        dest="upgrade",
        help="Don't upgrade dependencies as part of running uv sync",
    )

    return parser.parse_args(args)


def _version() -> str:
    return importlib.metadata.version(PROG)
