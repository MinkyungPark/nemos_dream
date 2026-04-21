"""Stage 3 entrypoint — Hydra-configured Pipeline over S1..S6.

Two execution modes:

* **Lightweight** (default, fast dev iteration) — sequential runner.
* **Curator** (``uv run python -m nemos_dream.stage3_validate_filter.runner
  --mode curator``) — uses ``curator_bridge.to_curator_stage`` + Ray executor.
"""

from __future__ import annotations

from pathlib import Path


def run(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    judge: str = "mock",
    mode: str = "lightweight",
    limit: int | None = None,
) -> dict[str, int]:
    """Execute stage 3. Returns ``{"accepted": N, "rejected": M}``."""
    raise NotImplementedError("stage 3 owner: implement")
