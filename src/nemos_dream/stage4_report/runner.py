"""Stage 4 entrypoint: ``Stage3Output`` streams → report + ``Stage4Sft`` rows."""

from __future__ import annotations

from pathlib import Path


def run(
    accepted_path: str | Path,
    rejected_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Render the report and emit the SFT JSONL.

    Returns a dict of emitted artifact paths. Internal structure (metrics,
    plots, templating, SFT export) is the owner's call.
    """
    raise NotImplementedError("stage 4 owner: implement")
