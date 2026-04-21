"""Stage 2a — initial Korean translation of the source text.

Produces a literal-enough Korean draft so that stage 2b can focus on cultural
rewriting rather than cross-lingual meaning transfer. Owner chooses the
backend (NIM chat, dedicated MT, …).
"""

from __future__ import annotations

from nemos_dream.schemas import Stage1Output


def translate(row: Stage1Output) -> str:
    """Return a Korean translation draft of ``row.source_text``."""
    raise NotImplementedError("stage 2 owner: implement")
