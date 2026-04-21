"""Stage 1b — attach Korean cultural equivalents to each ``CulturalRef``.

"어떤 말이 이 말로 바뀐다" — produce one ``MappedRef`` per English
``CulturalRef`` in the decomposed row. The owner picks the lookup strategy
(static dict, retriever, web-grounded, agent, …). The output contract is
simply ``list[MappedRef]``.
"""

from __future__ import annotations

from nemos_dream.schemas import CulturalRef, MappedRef


def map_refs(refs: list[CulturalRef]) -> list[MappedRef]:
    """Return a Korean mapping for each reference; empty list if none fit."""
    raise NotImplementedError("stage 1 owner: implement")
