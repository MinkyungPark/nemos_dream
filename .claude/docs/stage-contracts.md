# Stage contracts

The only authoritative source is `src/nemos_dream/schemas.py` — this file is
a human-readable index into it.

## Stage 0 — raw SODA-style dialogue

| | Schema | Location |
|---|---|---|
| Raw | `RawInput` | `data/raw/*.jsonl` |

A row is a multi-turn English dialogue with parallel `dialogue: list[str]` /
`speakers: list[str]` lists and a scene `narrative`. `original_index` is the
SODA row index; stage 1 assigns a canonical `id` (typically
`f"soda-{original_index}"`) and upgrades the parallel lists into structured
`list[Turn]` + `list[Speaker]`.

## Stage 1 — `stage1_decompose_map`

| | Schema | Location |
|---|---|---|
| Input | `RawInput` | `data/raw/*.jsonl` |
| Output | `Stage1Output` | `data/stage1/*.jsonl` |

**Invariants:**
* `len(source_dialogue) == len(RawInput.dialogue)` and every `Turn.index`
  is sequential starting at 0. `Turn.speaker` matches one of the
  `Speaker.name_en` values on the row.
* Every `CulturalRef.term` in `dialogue_decomposed.cultural_refs` must be a
  verbatim substring of some turn's `text` (case-insensitive).
* `len(mapped_refs) == len(dialogue_decomposed.cultural_refs)` (every ref
  gets a mapping, even if low-confidence — use `notes` to flag).
* Each `Speaker.dominant_emotion` is 1-5 intensity, and
  `dialogue_decomposed.overall_emotion` aggregates at the dialogue level —
  it does not have to equal any one speaker's emotion.
* Open-set strings (`scene.setting`, `scene.relationship_type`,
  `speakers[*].role_in_scene`, `speakers[*].gender_hint`) may expand as
  SODA coverage grows; no `Literal` gate blocks new values.

## Stage 2 — `stage2_translate_rewrite`

| | Schema | Location |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

**Invariants:**
* All `Stage1Output` fields are preserved verbatim — do **not** re-run
  decomposition or cultural mapping.
* `final_dialogue` is the final persona/style-conditioned KR rewrite.
  `step3_korean_dialogue` is the KR dialogue snapshot at step 3 of stage
  2's internal pipeline (usually equal to `final_dialogue` but preserved
  for regression analysis). Both preserve turn count and `Turn.index`
  alignment with `source_dialogue`.
* `Turn.speaker` in `final_dialogue` / `step3_korean_dialogue` is the
  **Korean name** (e.g. `"김나영"`) when persona localisation is applied.
  The mapping back to `Speaker.name_en` lives in `persona[i].speaker_name_en`
  and `persona[i].retrieved_persona.name`.
* `len(persona) == len(speakers)` and `{p.speaker_name_en for p in persona}
  == {s.name_en for s in speakers}`. Each `persona[i].speaker_index` is the
  index into `speakers` it applies to.
* For every `MappedRef` the stage chooses to apply, the corresponding
  Korean surface should appear in some turn of `final_dialogue` (stage 3
  may enforce strictly).
* **Deprecated v3 fields** (`korean_dialogue_draft`, `korean_dialogue`,
  `speaker_personas`, `speaker_styles`, `translation_meta`) remain readable
  for back-compat. A model validator mirrors `final_dialogue` ↔
  `korean_dialogue`, so consumers can read either name interchangeably.
  New writers should populate only the v4 fields.

## Stage 3 — `stage3_validate`

| | Schema | Location |
|---|---|---|
| Input | `Stage2Output` | `data/stage2/*.jsonl` |
| Output | `Stage3Output` | `data/stage3/{accepted,rejected}.jsonl` |

**Invariants:**
* A record never drops `Stage2Output` fields, regardless of `valid`.
* `valid == False` requires at least one entry in `reject_reasons`.
* `quality` fields are optional (`None`) if that check didn't run;
  populate whatever you measured. `semantic_cosine` is **deprecated** —
  cultural rewriting is not meaning preservation, so low EN↔KR cosine is
  often a feature not a bug. Use `intra_kr_coherence` (mean NV-Embed
  cosine between adjacent KR turns) as the quantitative flow signal.
* `retry_actions` are **hints** for the self-verify (NAT ReAct) agent —
  the agent may ignore, combine, or override them. Stage 3 never imports
  stage 1 or stage 2; the orchestrator owns the loop.
* `iter` starts at 0 on first pass and increments each time the
  self-verify agent re-runs the row through stages 1/2 and back through
  stage 3. Downstream readers can use `iter > 0` to filter for remediated
  rows.

**Reject semantics:** append a `RejectReason` and set `valid=False` rather
than raising. Exceptions are reserved for infrastructure failures (network,
schema parse errors) that belong in logs, not the output artifact.

## Stage 4 — `stage4_report`

| | Schema | Location |
|---|---|---|
| Input (accepted) | `Stage3Output` | `data/stage3/accepted.jsonl` |
| Input (rejected) | `Stage3Output` | `data/stage3/rejected.jsonl` |
| Output (SFT) | `Stage4Sft` | `data/reports/sft.jsonl` |
| Output (report) | — | `data/reports/report.{html,json,…}` |

**Invariants:**
* `Stage4Sft.messages` packages the dialogue in the OAI chat shape — the
  exact layout (single user/assistant pair vs. one message per turn) is
  configured in `configs/stage4/report.yaml`. The system prompt comes from
  the same config.
* `Stage4Sft.metadata.source_id == Stage3Output.id`.
* `Stage4Sft.metadata.domain` defaults to `"dialogue"` (multi-turn SFT),
  not `"sns"` — the pipeline emits conversational SFT, not single posts.

## Evolution rules

1. **Additive only** across stage boundaries. Never rename a field used by a
   downstream stage — add a new one and deprecate.
2. Bump `nemos_dream.__schema_version__` with every `schemas.py` change.
3. Grep `Stage{1,2,3}Output` across the repo after any edit to verify no
   consumer broke. The `update-schema` skill automates this.
4. Record the change (what, when, why) in a new section at the bottom of
   this file so future teammates understand the delta.

## Changelog

* **v4 (2026-04-21)** — stage-2 owner finalised a richer persona payload
  and localised KR speaker names. Additive over v3 (old fields stay
  readable):
  * `Stage2Output`: added `final_dialogue: list[Turn]`,
    `step3_korean_dialogue: list[Turn]`, and `persona: list[PersonaEntry]`.
    The old `korean_dialogue` is now optional (default `[]`) and is
    auto-mirrored from `final_dialogue` by a `model_validator`, so any
    existing reader of `row.korean_dialogue` keeps working.
    `korean_dialogue_draft`, `speaker_personas`, `speaker_styles`, and
    `translation_meta` are retained as deprecated optional fields.
  * New models: `PersonaEntry { speaker_index, speaker_name_en,
    retrieved_persona, selection_metadata, source_speaker_profile }`,
    `RetrievedPersona` (rich KR persona: name, age, age_bucket, sex,
    normalized_location, occupation, persona blurb, persona_id,
    summary_text, career_goals_and_ambitions, cultural_background,
    hobbies_and_interests, skills_and_expertise, extra),
    `PersonaSelectionMeta` (audit trail for how the persona was picked).
  * `Stage2Output.persona_speaker_names_en()` helper returns the set of
    English speaker names covered by either the v4 or v3 persona field,
    so consumer code (phase 2 `speaker_ref_integrity`) stays shape-agnostic.
  * No stage-3 / stage-4 schema changes; stage 3 consumers were updated
    to read `persona` when populated and fall back to the v3 field.

* **v3 (2026-04-21)** — pipeline pivoted from single-SNS-post to multi-turn
  SODA dialogue. Breaking scaffold-phase rewrite (no stage implementations
  existed yet, so no production data to migrate):
  * `RawInput`: `source_text: str` → `dialogue: list[str]` +
    `speakers: list[str]` + `narrative: str` + `original_index: int`.
  * `Stage1Output`: replaced `decomposed: Decomposed` with
    `source_dialogue: list[Turn]` + `speakers: list[Speaker]` +
    `scene: Scene` + `dialogue_decomposed: DialogueDecomposed`.
  * `Stage2Output`: replaced `ko_text_draft` / `ko_text` / `rewrite_meta`
    with `korean_dialogue_draft: list[Turn]` + `korean_dialogue: list[Turn]`
    + `speaker_personas: list[Persona]` + `speaker_styles: list[Style]` +
    `translation_meta: dict`. `Persona` carries the team's nine-attribute
    bank (성별/나이/직업/학력/결혼여부/군대여부/가족형태/집주거여부/전공);
    `Style` carries the four signals (격식체/감정/마커/말하는스타일).
  * `Stage3Output`: added `retry_actions: list[RetryAction]` + `iter: int`
    for the self-verify loop; added `QualityScores.persona_style_consistency`,
    `QualityScores.intra_kr_coherence`, `QualityScores.judge_reasoning`;
    deprecated `QualityScores.semantic_cosine` (kept for back-compat).
  * `MappedRef`: added `validation: list[dict]` for per-ref provenance.
  * `SftMetadata`: `domain` default `"sns"` → `"dialogue"`; `target_platform`
    relaxed to `Optional[Platform]`.
* **v2 (2026-04-21)** — renamed `Stage2Output.ko_text_pre_marker` →
  `ko_text_draft` (more neutral: stage 2's first pass is a translation draft,
  not a marker-specific intermediate). Added `RewriteMeta.extra: dict` to
  honor "Metadata 추가될 수 있음" without future schema churn. No stage
  implementations existed yet, so this was a scaffold-phase rename rather
  than a breaking migration. Superseded by v3.
