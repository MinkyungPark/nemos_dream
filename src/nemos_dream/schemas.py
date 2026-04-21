"""Canonical Pydantic contract shared across all four stages.

This is the ONLY module with real logic during the scaffold phase — every
teammate imports from here, so stubbing it would block everyone. Changes must
follow the rules in ``.claude/skills/update-schema/SKILL.md``:

1. Inter-stage fields are **additive only** — never rename or remove.
2. Bump ``nemos_dream.__schema_version__`` when you change this file.
3. Update ``.claude/docs/stage-contracts.md`` with the migration note.

Layering (each stage emits its predecessor's fields plus its own):

    RawInput       : {id, source_text}
    Stage1Output   : RawInput      + {decomposed, mapped_refs}
    Stage2Output   : Stage1Output  + {ko_text, ko_text_pre_marker, rewrite_meta}
    Stage3Output   : Stage2Output  + {quality, valid, reject_reasons}
    Stage4Sft      : {messages, metadata}   # final SFT row — OAI chat shape
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

warnings.filterwarnings(
    "ignore",
    message=r'Field name "register" .*shadows an attribute in parent .*',
)


# ---------------------------------------------------------------------------
# Enumerations (keep literal sets in sync with prompts in each stage)
# ---------------------------------------------------------------------------

SpeechAct = Literal[
    "complaint",
    "brag",
    "question",
    "empathy_seeking",
    "sarcasm",
    "joke",
    "statement",
    "greeting",
    "request",
    "announce",
    "advice",
    "other",
]
Register = Literal["intimate", "casual", "formal", "public"]
EmotionType = Literal["joy", "anger", "sadness", "fear", "surprise", "disgust", "neutral"]
CulturalRefType = Literal[
    "holiday",
    "brand",
    "service",
    "event",
    "person",
    "food",
    "place",
    "pop_culture",
    "meme",
    "slang",
    "other",
]
Laughter = Literal["lol", "lmao", "rofl", "haha", "none"]
Emphasis = Literal["CAPS", "repetition", "punctuation", "emoji", "exclaim", "ellipsis"]
AgeGroup = Literal["teen", "20s", "30s", "40plus", "unknown"]
Platform = Literal["twitter", "reddit", "instagram", "tiktok", "discord", "sms", "thread"]
MapSource = Literal["dict", "retriever", "web+llm"]
GenderStyle = Literal["masc", "fem", "neutral"]


# ---------------------------------------------------------------------------
# Stage 1 — sociolinguistic decomposition + cultural ref mapping
# ---------------------------------------------------------------------------


class Emotion(BaseModel):
    type: EmotionType
    intensity: int = Field(ge=1, le=5)


class CulturalRef(BaseModel):
    type: CulturalRefType
    term: str


class InternetMarkers(BaseModel):
    laughter: Laughter = "none"
    emphasis: list[Emphasis] = Field(default_factory=list)
    sarcasm_marker: bool = False


class Decomposed(BaseModel):
    """Stage-1 sociolinguistic meta extracted from a raw English post."""

    source_text: str
    speech_act: SpeechAct
    register: Register
    emotion: Emotion
    cultural_refs: list[CulturalRef] = Field(default_factory=list)
    internet_markers: InternetMarkers
    estimated_age_group: AgeGroup
    platform_fit: list[Platform] = Field(default_factory=list)


class MappedRef(BaseModel):
    """One English-→-Korean cultural reference mapping, with provenance."""

    term: str
    ko: str
    type: str
    source: MapSource
    retrieved: bool = False
    notes: str = ""


class RawInput(BaseModel):
    id: str
    source_text: str


class Stage1Output(BaseModel):
    """Shape that stage 1 writes to ``data/stage1/*.jsonl``."""

    id: str
    source_text: str
    decomposed: Decomposed
    mapped_refs: list[MappedRef] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2 — metadata-conditioned Korean rewriting + marker injection
# ---------------------------------------------------------------------------


class RewriteMeta(BaseModel):
    """Target-side generation hints that stage 2 commits to per row."""

    target_platform: Platform
    target_age_group: AgeGroup
    target_community: str = ""
    target_gender_style: GenderStyle = "neutral"
    persona_id: str | None = None


class Stage2Output(Stage1Output):
    """Stage 2 adds Korean text (pre- and post-marker) plus rewrite targeting."""

    ko_text_pre_marker: str
    ko_text: str
    rewrite_meta: RewriteMeta


# ---------------------------------------------------------------------------
# Stage 3 — validation / filtering / scoring
# ---------------------------------------------------------------------------


class QualityScores(BaseModel):
    semantic_cosine: float | None = None
    property_preservation: int | None = Field(default=None, ge=1, le=5)
    naturalness: int | None = Field(default=None, ge=1, le=5)
    cultural_appropriateness: int | None = Field(default=None, ge=1, le=5)
    register_consistency: int | None = Field(default=None, ge=1, le=5)
    safety_pass: bool | None = None
    pii_pass: bool | None = None
    aggregate: float | None = None
    reward: dict[str, float] | None = None


class RejectReason(BaseModel):
    stage: str
    rule: str | None = None
    detail: str
    extra: dict[str, Any] = Field(default_factory=dict)


class Stage3Output(Stage2Output):
    """Stage 3 attaches quality scores + accept/reject decision."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    quality: QualityScores = Field(default_factory=QualityScores)
    valid: bool = True
    reject_reasons: list[RejectReason] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 — SFT export row (OpenAI chat shape, matches meta_data.json example)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class SftQualityScore(BaseModel):
    score: int = Field(ge=1, le=5)


class SftMetadata(BaseModel):
    source_id: str
    domain: str = "sns"
    target_platform: Platform
    target_age_group: AgeGroup
    target_community: str = ""
    target_gender_style: GenderStyle = "neutral"
    quality_score: dict[str, SftQualityScore] = Field(default_factory=dict)


class Stage4Sft(BaseModel):
    """Final SFT training row emitted by stage 4."""

    messages: list[ChatMessage]
    metadata: SftMetadata
