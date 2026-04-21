"""Stage 2 helper — pick a Korean persona for style scale-up.

Backed by ``nvidia/Nemotron-Personas-Korea`` (HF dataset). The chosen persona
becomes ``RewriteMeta.persona_id`` and is threaded into the rewrite prompt.
"""

from __future__ import annotations

from nemos_dream.schemas import AgeGroup, GenderStyle, Platform, RewriteMeta


def pick_persona(
    *,
    platform: Platform,
    age_group: AgeGroup,
    gender_style: GenderStyle = "neutral",
    community: str = "",
) -> RewriteMeta:
    """Return a :class:`RewriteMeta` whose ``persona_id`` is drawn from HF."""
    raise NotImplementedError("stage 2 owner: implement")
