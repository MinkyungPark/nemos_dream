"""Stage 3 entrypoint: ``Stage2Output`` rows → ``Stage3Output`` rows (+ reject bucket)."""

from __future__ import annotations

from pathlib import Path


def run(input_path: str | Path, output_dir: str | Path) -> dict[str, int]:
    """Run stage 3 end-to-end.

    Expected to write ``accepted.jsonl`` and ``rejected.jsonl`` under
    ``output_dir`` and return ``{"accepted": N, "rejected": M}``. Internal
    decomposition (rules vs. safety vs. dedup vs. judge vs. reward) is the
    owner's call.
    """
    raise NotImplementedError("stage 3 owner: implement")
