"""End-to-end pipeline entrypoint: stages 1 → 2 → 3 → 4.

Usage (dev)::

    uv run python scripts/run_pipeline.py \
        --input data/raw/sample_input.jsonl \
        --output-dir data/ \
        --limit 10
"""

from __future__ import annotations

import argparse


def main() -> int:
    raise NotImplementedError("pipeline owner: wire up stage runners")


if __name__ == "__main__":
    raise SystemExit(main())
