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
    Stage2Output   : Stage1Output + {final_dialogue, step3_korean_dialogue,
                                     persona}
                     (+ deprecated v3 fields: korean_dialogue_draft,
                      korean_dialogue, speaker_personas, speaker_styles,
                      translation_meta — kept optional for back-compat)
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

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    """**DEPRECATED (v3)** — 9-attribute Korean persona shape.

    Superseded by ``PersonaEntry`` / ``RetrievedPersona`` in v4. Kept for
    back-compat with rows produced by earlier stage 2 runs. New writers
    should populate ``Stage2Output.persona`` instead of ``speaker_personas``.
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
    """**DEPRECATED (v3)** — per-speaker style overlay.

    Stage 2 v4 folds style signals into the ``retrieved_persona`` payload
    and ``Speaker`` metadata; this model is retained only to parse rows
    emitted by earlier stage 2 runs.
    """

    speaker_ref: str
    formality: Register
    emotion: Emotion
    markers: InternetMarkers = Field(default_factory=InternetMarkers)
    speech_style_notes: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class RetrievedPersona(BaseModel):
    """Rich Korean persona retrieved from the persona bank (v4).

    Fields mirror ``nvidia/Nemotron-Personas-Korea`` columns. ``name`` is
    the Korean speaker name that replaces the English ``Speaker.name_en``
    in ``Stage2Output.final_dialogue[*].speaker``.
    """

    name: str
    age: int
    age_bucket: str = ""
    sex: str = ""
    normalized_location: str = ""
    occupation: str = ""
    persona: str = ""
    persona_id: str = ""
    summary_text: str = ""
    career_goals_and_ambitions: str = ""
    cultural_background: str = ""
    hobbies_and_interests: str = ""
    skills_and_expertise: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class PersonaSelectionMeta(BaseModel):
    """Audit trail for how a persona was chosen from the bank."""

    candidate_age_buckets: list[str] = Field(default_factory=list)
    candidate_gender: str = ""
    keyword_hints: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    matched_by_keywords: bool = False
    selected_random_age_group: bool = False
    selected_random_gender: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class PersonaEntry(BaseModel):
    """One persona assignment for a stage-1 speaker (v4 shape).

    ``speaker_name_en`` and ``speaker_index`` tie the entry back to the
    stage-1 ``Speaker`` / ``source_dialogue`` position. ``retrieved_persona``
    is the KR persona applied; ``source_speaker_profile`` snapshots the
    stage-1 ``Speaker`` record used for selection (same shape as
    :class:`Speaker`).
    """

    speaker_index: int
    speaker_name_en: str
    retrieved_persona: RetrievedPersona
    selection_metadata: PersonaSelectionMeta = Field(
        default_factory=PersonaSelectionMeta
    )
    source_speaker_profile: Speaker


class Stage2Output(Stage1Output):
    """Stage-1 fields preserved verbatim + Korean rewrite + persona payload.

    **v4 canonical fields** (populated by the current stage-2 runner):

    - ``final_dialogue``: final persona/style-conditioned KR dialogue.
    - ``step3_korean_dialogue``: snapshot of the KR dialogue at step 3 of
      stage 2's internal pipeline (usually equal to ``final_dialogue`` but
      preserved for regression analysis).
    - ``persona``: list of :class:`PersonaEntry`, one per stage-1 speaker.

    **v3 deprecated fields** (optional; mirrored by the validator below so
    either side is readable):

    - ``korean_dialogue_draft`` / ``korean_dialogue`` / ``speaker_personas``
      / ``speaker_styles`` / ``translation_meta``.

    A model-validator mirrors ``final_dialogue`` ↔ ``korean_dialogue`` after
    construction so every downstream reader can pick either name and get
    the same turns.
    """

    # v4 canonical
    final_dialogue: list[Turn] = Field(default_factory=list)
    step3_korean_dialogue: list[Turn] = Field(default_factory=list)
    persona: list[PersonaEntry] = Field(default_factory=list)

    # v3 deprecated (kept optional for back-compat)
    korean_dialogue_draft: list[Turn] = Field(default_factory=list)
    korean_dialogue: list[Turn] = Field(default_factory=list)
    speaker_personas: list[Persona] = Field(default_factory=list)
    speaker_styles: list[Style] = Field(default_factory=list)
    translation_meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _mirror_kr_dialogue(self) -> Stage2Output:
        """Make ``final_dialogue`` and ``korean_dialogue`` interchangeable.

        Accepts rows that populate only one side and backfills the other
        with the same turn list. If both are populated (v4 writers may do
        this explicitly) they are left untouched.
        """
        if self.final_dialogue and not self.korean_dialogue:
            self.korean_dialogue = list(self.final_dialogue)
        elif self.korean_dialogue and not self.final_dialogue:
            self.final_dialogue = list(self.korean_dialogue)
        return self

    def persona_speaker_names_en(self) -> set[str]:
        """English speaker names covered by the populated persona field.

        Prefers v4 ``persona`` when non-empty, falls back to v3
        ``speaker_personas``. Used by stage 3 for speaker-ref integrity.
        """
        if self.persona:
            return {p.speaker_name_en for p in self.persona}
        return {p.speaker_ref for p in self.speaker_personas}


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
