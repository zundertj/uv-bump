import argparse
from pathlib import Path

from uv_bump.main import upgrade


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="uv-bump",
        description=(
            "UV-bump updates your pyproject.toml minimum versions to the latest"
            " feasible version"
        ),
    )

    parser.add_argument(
        "--pyproject-toml",
        help="File to update",
    )

    args = parser.parse_args()

    upgrade(Path(args.pyproject_toml) if args.pyproject_toml is not None else None)
