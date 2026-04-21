"""Distribution analysis over decomposed / rewrite metadata."""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output


def distribution_by(rows: list[Stage3Output], field: str) -> dict[str, int]:
    """Count occurrences of each value of a dotted-path ``field`` (e.g. ``"decomposed.register"``)."""
    raise NotImplementedError("stage 4 owner: implement")
