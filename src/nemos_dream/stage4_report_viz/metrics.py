"""Aggregate quality metrics across a stage-3 output set."""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output


def aggregate_quality(rows: list[Stage3Output]) -> dict[str, float]:
    """Mean and median per axis plus overall pass rate."""
    raise NotImplementedError("stage 4 owner: implement")


def top_reject_reasons(rows: list[Stage3Output], n: int = 10) -> list[dict]:
    """Top-``n`` (stage, rule) pairs with counts and sample detail strings."""
    raise NotImplementedError("stage 4 owner: implement")
