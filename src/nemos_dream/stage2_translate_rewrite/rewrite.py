"""Stage 2b — persona / style-conditioned rewrite of the Korean draft.

Conditions on stage-1 metadata (``scene`` + ``dialogue_decomposed`` +
``mapped_refs``) and per-speaker ``Persona`` / ``Style`` overlays to produce
the final Korean dialogue. This is where cultural substitution, register,
internet markers, persona flavour, etc. get applied.

Output goes into ``Stage2Output.korean_dialogue``; the pre-rewrite Korean
draft (from ``translate.translate``) goes into ``korean_dialogue_draft``.
Ad-hoc metadata about the rewrite pass belongs in
``Stage2Output.translation_meta`` (open dict).
"""

from __future__ import annotations

from nemos_dream.schemas import Persona, Stage1Output, Style, Turn


def rewrite(
    row: Stage1Output,
    ko_draft: list[Turn],
    personas: list[Persona],
    styles: list[Style],
) -> list[Turn]:
    """Return the final Korean dialogue (one ``Turn`` per source turn)."""
    raise NotImplementedError("stage 2 owner: implement")
