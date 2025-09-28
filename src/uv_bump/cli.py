import argparse
import importlib.metadata
import sys
from collections.abc import Sequence
from pathlib import Path

from uv_bump.main import upgrade

PROG = "uv-bump"


def cli() -> None:
    args = parse_args(sys.argv[1:])
    upgrade(Path(args.pyproject_toml) if args.pyproject_toml is not None else None)


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

    return parser.parse_args(args)


def _version() -> str:
    return importlib.metadata.version(PROG)
