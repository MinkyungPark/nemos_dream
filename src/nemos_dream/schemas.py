"""Canonical Pydantic contract shared across all four stages.

This is the ONLY module with real logic during the scaffold phase — every
teammate imports from here, so stubbing it would block everyone. Changes must
follow the rules in ``.claude/skills/update-schema/SKILL.md``:

1. Inter-stage fields are **additive only** — never rename or remove.
2. Bump ``nemos_dream.__schema_version__`` when you change this file.
3. Update ``.claude/docs/stage-contracts.md`` with the migration note.

Pipeline shape (multi-turn dialogue, SODA-based):

    RawInput       : {id?, original_index, dialogue, speakers, narrative}
    Stage1Output   : {id, original_index, source_dialogue, speakers, scene,
                      dialogue_decomposed, mapped_refs}
    Stage2Output   : Stage1Output + {korean_dialogue_draft, korean_dialogue,
                                     speaker_personas, speaker_styles,
                                     translation_meta}
    Stage3Output   : Stage2Output + {quality, valid, reject_reasons,
                                     retry_actions, iter}
    Stage4Sft      : {messages, metadata}   # OAI chat shape

``RawInput`` is **not** a base class of ``Stage1Output`` — raw data stores
``dialogue: list[str]`` / ``speakers: list[str]`` as parallel lists, while
stage 1 upgrades these into structured ``list[Turn]`` + ``list[Speaker]``.
Stage-2+ layering (``Stage2Output`` ⊂ ``Stage1Output`` ⊂ ``Stage3Output``)
is preserved so downstream stages never drop upstream fields.
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

# Open-set strings (stage 1 owner expands as SODA coverage grows, so we do not
# lock these into ``Literal``): ``Scene.setting``, ``Scene.relationship_type``,
# ``Speaker.role_in_scene``, ``Speaker.gender_hint``, and every ``Persona.*``
# attribute.


# ---------------------------------------------------------------------------
# Primitives shared across stages
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


class MappedRef(BaseModel):
    """One English-→-Korean cultural reference mapping, with provenance.

    ``validation`` is an open list of per-ref validation records that stage 1
    (or the self-verify agent) attaches. Shape is intentionally loose until
    the stage-1 owner formalises it.
    """

    term: str
    ko: str
    type: str
    source: MapSource
    retrieved: bool = False
    notes: str = ""
    validation: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 0 — raw SODA-style dialogue input
# ---------------------------------------------------------------------------


class RawInput(BaseModel):
    """Raw dialogue row as written to ``data/raw/*.jsonl``.

    Stage 1 assigns a canonical ``id`` (typically ``f"soda-{original_index}"``)
    and upgrades the parallel ``dialogue`` / ``speakers`` string lists into
    structured ``list[Turn]`` + ``list[Speaker]``.
    """

    id: str | None = None
    original_index: int
    dialogue: list[str]
    speakers: list[str]
    narrative: str = ""


# ---------------------------------------------------------------------------
# Stage 1 — dialogue decomposition + cultural-ref mapping
# ---------------------------------------------------------------------------


class Turn(BaseModel):
    """One utterance in a dialogue."""

    index: int
    speaker: str  # matches ``Speaker.name_en`` (or the Korean name in stage 2)
    text: str


class Speaker(BaseModel):
    """English-side speaker metadata extracted by stage 1."""

    name_en: str
    role_in_scene: str
    gender_hint: str = "unknown"
    age_group_hint: AgeGroup = "unknown"
    register: Register
    dominant_emotion: Emotion
    personality_traits: list[str] = Field(default_factory=list)
    interests_hints: list[str] = Field(default_factory=list)
    occupation_hint: str = ""
    speech_style_notes: str = ""


class Scene(BaseModel):
    """Scene-level context decomposed from the dialogue."""

    narrative_en: str = ""
    setting: str = "other"  # home|workplace|school|online|other|...
    relationship_type: str = "other"  # friendship|professional|acquaintance|...
    topics: list[str] = Field(default_factory=list)


class DialogueDecomposed(BaseModel):
    """Dialogue-level sociolinguistic meta (aggregate across speakers)."""

    overall_register: Register
    overall_emotion: Emotion
    speech_acts: list[SpeechAct] = Field(default_factory=list)
    cultural_refs: list[CulturalRef] = Field(default_factory=list)


class Stage1Output(BaseModel):
    """Shape stage 1 writes to ``data/stage1/*.jsonl``."""

    id: str
    original_index: int
    source_dialogue: list[Turn]
    speakers: list[Speaker]
    scene: Scene
    dialogue_decomposed: DialogueDecomposed
    mapped_refs: list[MappedRef] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2 — persona / style-conditioned Korean rewriting
# ---------------------------------------------------------------------------


class Persona(BaseModel):
    """Korean persona attached to a translated speaker.

    Core nine attributes come from the team's persona bank (e.g.
    ``nvidia/Nemotron-Personas-Korea``): gender, age, occupation, education
    (학력), marital_status (결혼여부), military_status (군대여부),
    family_type (가족형태), housing (집주거여부), major (전공). ``extra`` is
    an open slot for ad-hoc persona signals.

    ``speaker_ref`` matches the ``Speaker.name_en`` this persona applies to,
    so readers can zip personas back to stage-1 speakers unambiguously.
    """

    speaker_ref: str
    gender: str = "unknown"
    age: str = "unknown"
    occupation: str = ""
    education: str = ""
    marital_status: str = ""
    military_status: str = ""
    family_type: str = ""
    housing: str = ""
    major: str = ""
    persona_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class Style(BaseModel):
    """Per-speaker style overlay applied during rewriting.

    Carries the four style signals: formality (격식체), emotion (감정),
    markers (마커), and speech_style_notes (말하는 스타일).
    """

    speaker_ref: str
    formality: Register
    emotion: Emotion
    markers: InternetMarkers = Field(default_factory=InternetMarkers)
    speech_style_notes: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class Stage2Output(Stage1Output):
    """Stage-1 fields preserved verbatim + Korean rewrite + persona/style."""

    korean_dialogue_draft: list[Turn] = Field(default_factory=list)
    korean_dialogue: list[Turn]
    speaker_personas: list[Persona] = Field(default_factory=list)
    speaker_styles: list[Style] = Field(default_factory=list)
    translation_meta: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage 3 — validation / filtering / scoring
# ---------------------------------------------------------------------------


class QualityScores(BaseModel):
    """Quality signals attached by stage 3.

    All fields are optional — populate what the pipeline measured, leave the
    rest ``None``. Judge axes are 1-5 integers.

    ``semantic_cosine`` (EN↔KR embedding cosine) is **deprecated** — cultural
    rewriting is not meaning preservation, so low EN↔KR cosine is often a
    feature not a bug. ``intra_kr_coherence`` (mean NV-Embed cosine between
    adjacent KR turns) replaces it as the quantitative flow signal.
    """

    # Judge rubric (1-5)
    property_preservation: int | None = Field(default=None, ge=1, le=5)
    naturalness: int | None = Field(default=None, ge=1, le=5)
    cultural_appropriateness: int | None = Field(default=None, ge=1, le=5)
    register_consistency: int | None = Field(default=None, ge=1, le=5)
    persona_style_consistency: int | None = Field(default=None, ge=1, le=5)

    # Quantitative
    intra_kr_coherence: float | None = None
    semantic_cosine: float | None = None  # DEPRECATED — retained for back-compat

    # Guardrails
    safety_pass: bool | None = None
    pii_pass: bool | None = None

    # Aggregates
    aggregate: float | None = None
    reward: dict[str, float] | None = None

    # Per-axis judge reasoning — fed to the self-verify agent as remediation context
    judge_reasoning: dict[str, str] | None = None


class RejectReason(BaseModel):
    stage: str
    rule: str | None = None
    detail: str
    extra: dict[str, Any] = Field(default_factory=dict)


RetryActionKind = Literal[
    "stage1_redecompose",
    "maps_ref_redo",
    "stage2_rewrite",
    "websearch_cultural",
    "none",
]


class RetryAction(BaseModel):
    """Stage-3 suggestion for the self-verify (NAT ReAct) agent.

    The agent is free to ignore / combine / override these — they are hints,
    not commands. ``hints`` carries action-specific payloads (e.g. which axis
    failed, which cultural term to re-resolve).
    """

    action: RetryActionKind
    reason_summary: str = ""
    hints: dict[str, Any] = Field(default_factory=dict)


class Stage3Output(Stage2Output):
    """Stage 3 attaches quality scores, reject reasons, and retry hints."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    quality: QualityScores = Field(default_factory=QualityScores)
    valid: bool = True
    reject_reasons: list[RejectReason] = Field(default_factory=list)
    retry_actions: list[RetryAction] = Field(default_factory=list)
    iter: int = 0  # which self-verify iteration produced this row (0 = first pass)


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
    domain: str = "dialogue"
    target_platform: Platform | None = None
    target_age_group: AgeGroup | None = None
    target_community: str = ""
    target_gender_style: GenderStyle = "neutral"
    quality_score: dict[str, SftQualityScore] = Field(default_factory=dict)


class Stage4Sft(BaseModel):
    """Final SFT training row emitted by stage 4."""

    messages: list[ChatMessage]
    metadata: SftMetadata
