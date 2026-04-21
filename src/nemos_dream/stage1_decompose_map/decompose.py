"""Stage 1a — sociolinguistic decomposition: ``RawInput`` → ``Decomposed``.

Extracts speech act, register, emotion, internet markers, cultural references,
etc. from the raw English source text. The owner chooses the backend (Data
Designer, direct NIM, agent toolkit) — this module just has to return the
``Decomposed`` shape defined in ``nemos_dream.schemas``.
"""

from __future__ import annotations

from collections.abc import Iterable

from nemos_dream.schemas import Decomposed, RawInput


def decompose(rows: Iterable[RawInput]) -> list[Decomposed]:
    """Return one ``Decomposed`` per input row, in input order."""
    raise NotImplementedError("stage 1 owner: implement")
