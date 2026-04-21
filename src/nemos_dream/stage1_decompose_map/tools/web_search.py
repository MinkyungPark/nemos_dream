"""Web-grounded fallback: Tavily search + Nemotron reasoning."""

from __future__ import annotations

from nemos_dream.schemas import MappedRef


def web_llm_map(term: str, *, ref_type: str) -> MappedRef:
    """Search the open web for ``term`` and synthesise a Korean mapping.

    Always returns a :class:`MappedRef` (never ``None``) with ``source='web+llm'``.
    If no confident Korean equivalent exists, return the romanisation plus
    a warning in ``notes``.
    """
    raise NotImplementedError("stage 1 owner: implement")
