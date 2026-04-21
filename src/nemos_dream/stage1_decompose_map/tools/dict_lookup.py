"""Exact-match lookup against ``configs/stage1/cultural_map_seed.json``."""

from __future__ import annotations

from nemos_dream.schemas import MappedRef


def dict_lookup(term: str, *, ref_type: str) -> MappedRef | None:
    """Return a ``MappedRef`` with ``source='dict'`` or ``None`` on miss."""
    raise NotImplementedError("stage 1 owner: implement")


def append_to_dict(mapped: MappedRef) -> None:
    """Persist a newly-discovered mapping back to the seed JSON."""
    raise NotImplementedError("stage 1 owner: implement")
