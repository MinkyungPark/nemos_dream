"""Stage 2 entrypoint: ``Stage1Output`` rows → ``Stage2Output`` rows."""

from __future__ import annotations

from pathlib import Path


def run(input_path: str | Path, output_path: str | Path) -> int:
    """Run stage 2 end-to-end. Returns number of rows written."""
    raise NotImplementedError("stage 2 owner: implement")
