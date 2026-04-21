"""Stage 2a — initial Korean translation of the English dialogue.

Produces a literal-enough Korean draft per turn so that stage 2b can focus on
cultural rewriting rather than cross-lingual meaning transfer. Owner chooses
the backend (NIM chat, dedicated MT, …).

Turn ordering and speaker labels must match ``row.source_dialogue`` one-to-one
— stage 2b relies on parallel indexing to attach per-speaker persona / style.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage1Output, Turn


def translate(row: Stage1Output) -> list[Turn]:
    """Return a Korean translation draft of ``row.source_dialogue``."""
    raise NotImplementedError("stage 2 owner: implement")
