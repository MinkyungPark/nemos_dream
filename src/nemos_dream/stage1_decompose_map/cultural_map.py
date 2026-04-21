"""Stage 1b — map every ``CulturalRef`` to a Korean equivalent.

Deterministic chain (default): ``dict → retriever → web+llm``.
The first route that produces a confident hit wins. Web+LLM results are
auto-appended back to ``configs/stage1/cultural_map_seed.json`` (self-growing
cache).

Alternative: set ``MAP_REFS_USE_NAT=1`` to switch to the NeMo Agent Toolkit
ReAct workflow (``configs/stage1/cultural_agent.yaml``).
"""

from __future__ import annotations

from nemos_dream.schemas import CulturalRef, MappedRef


def map_refs(refs: list[CulturalRef]) -> list[MappedRef]:
    """Resolve each ``CulturalRef`` through the deterministic chain."""
    raise NotImplementedError("stage 1 owner: implement")


def map_refs_nat(refs: list[CulturalRef]) -> list[MappedRef]:
    """Opt-in ReAct-agent variant backed by NeMo Agent Toolkit."""
    raise NotImplementedError("stage 1 owner: implement")
