"""Stage 1 entrypoint: load → decompose → map → write ``Stage1Output``."""

from __future__ import annotations

from pathlib import Path


def run(
    input_path: str | Path,
    output_path: str | Path,
    *,
    limit: int | None = None,
    use_nat: bool = False,
) -> int:
    """Execute stage 1 end-to-end. Returns number of rows written."""
    raise NotImplementedError("stage 1 owner: implement")
