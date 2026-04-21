"""Stage 1a — sociolinguistic decomposition of a SODA-style dialogue.

Takes a raw multi-turn dialogue and extracts structured per-speaker metadata
(``Speaker``), scene-level context (``Scene``), and dialogue-level aggregate
signals (``DialogueDecomposed``), plus an aligned ``list[Turn]``.

The owner chooses the backend (Data Designer, direct NIM, agent toolkit) —
this module only has to return the four shapes defined in
``nemos_dream.schemas``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from nemos_dream.schemas import (
    DialogueDecomposed,
    RawInput,
    Scene,
    Speaker,
    Turn,
)


class DecomposeResult(NamedTuple):
    turns: list[Turn]
    speakers: list[Speaker]
    scene: Scene
    dialogue_decomposed: DialogueDecomposed


def decompose(rows: Iterable[RawInput]) -> list[DecomposeResult]:
    """Return one ``DecomposeResult`` per input row, in input order."""
    raise NotImplementedError("stage 1 owner: implement")
