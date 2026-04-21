"""Stage 1 entrypoint: read ``RawInput`` rows → emit ``Stage1Output`` rows."""

from __future__ import annotations

from pathlib import Path


def run(input_path: str | Path, output_path: str | Path) -> int:
    """Run stage 1 end-to-end. Returns number of rows written."""
    raise NotImplementedError("stage 1 owner: implement")
