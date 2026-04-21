"""Shared IO — JSONL read/write + Hugging Face dataset loader.

Signatures only. Owner: whoever needs it first (likely stage 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def read_jsonl(path: str | Path, model: type[ModelT]) -> Iterator[ModelT]:
    """Yield one validated ``model`` instance per line of a JSONL file."""
    raise NotImplementedError("shared owner: implement")


def write_jsonl(path: str | Path, rows: Iterable[BaseModel]) -> int:
    """Write ``rows`` (Pydantic models) to ``path``. Returns count written."""
    raise NotImplementedError("shared owner: implement")


def load_hf_dataset(
    spec: str,
    *,
    limit: int | None = None,
    text_field: str = "text",
    id_field: str | None = None,
) -> Iterator[dict]:
    """Load a HuggingFace dataset by spec ``hf:owner/name:split``.

    Yields ``{id, source_text}`` dicts shaped like :class:`schemas.RawInput`.
    """
    raise NotImplementedError("shared owner: implement")
