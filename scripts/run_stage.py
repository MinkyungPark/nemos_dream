"""Run a single stage by number.

Usage::

    uv run python scripts/run_stage.py --stage 1 --input ... --output ...
    uv run python scripts/run_stage.py --stage 2 --input ... --output ...
    uv run python scripts/run_stage.py --stage 3 --input ... --output-dir ...
    uv run python scripts/run_stage.py --stage 4 \
        --accepted ... --rejected ... --output-dir ...
"""

from __future__ import annotations

import argparse


def main() -> int:
    raise NotImplementedError("pipeline owner: dispatch to stage runners")


if __name__ == "__main__":
    raise SystemExit(main())
