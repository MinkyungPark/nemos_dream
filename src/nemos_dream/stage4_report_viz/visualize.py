"""Chart generation — matplotlib PNGs + plotly HTML widgets."""

from __future__ import annotations

from pathlib import Path


def render_histogram(counts: dict[str, int], *, title: str, out_path: str | Path) -> Path:
    """Write a labelled histogram PNG. Returns the written path."""
    raise NotImplementedError("stage 4 owner: implement")


def render_quality_radar(axes: dict[str, float], *, out_path: str | Path) -> Path:
    """Radar chart of the 4 quality axes + reward aggregate."""
    raise NotImplementedError("stage 4 owner: implement")
