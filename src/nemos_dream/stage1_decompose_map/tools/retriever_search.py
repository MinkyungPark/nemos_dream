"""Cosine-similarity lookup via NeMo Retriever embeddings."""

from __future__ import annotations

from nemos_dream.schemas import MappedRef


def retriever_search(
    term: str,
    *,
    ref_type: str,
    threshold: float = 0.65,
) -> MappedRef | None:
    """Return a ``MappedRef`` with ``source='retriever'`` if score ≥ threshold."""
    raise NotImplementedError("stage 1 owner: implement")


def build_index() -> None:
    """(Re)build ``configs/stage1/retriever_index.npz`` from the seed dict."""
    raise NotImplementedError("stage 1 owner: implement")
