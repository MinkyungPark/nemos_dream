# Stage contracts

The only authoritative source is `src/nemos_dream/schemas.py` — this file is
a human-readable index into it.

## Stage 1 — `stage1_decompose_map`

| | Schema | Location |
|---|---|---|
| Input | `RawInput` | `data/raw/*.jsonl` |
| Output | `Stage1Output` | `data/stage1/*.jsonl` |

**Invariants:**
* Every `CulturalRef.term` in `decomposed.cultural_refs` must be a verbatim
  substring of `source_text` (case-insensitive).
* `len(mapped_refs) == len(decomposed.cultural_refs)` (every ref gets a
  mapping, even if low-confidence — use `notes` to flag).
* `internet_markers.laughter` ∈ {lol, lmao, rofl, haha, none}; pick `none`
  if uncertain — never infer.

## Stage 2 — `stage2_translate_rewrite`

| | Schema | Location |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

**Invariants:**
* All `Stage1Output` fields are preserved verbatim — do **not** re-run
  decomposition or cultural mapping.
* `ko_text_draft` is the initial Korean translation of `source_text`;
  `ko_text` is the final rewrite (cultural / register / marker post-processing).
* For every `MappedRef` that the stage chooses to apply, the corresponding
  Korean surface should appear in `ko_text` (stage 3 may enforce strictly).
* `rewrite_meta.extra` is an open dict for ad-hoc targeting signals — use it
  instead of inventing new top-level fields. Promote keys that stick to real
  `RewriteMeta` fields via the `update-schema` skill.

## Stage 3 — `stage3_validate`

| | Schema | Location |
|---|---|---|
| Input | `Stage2Output` | `data/stage2/*.jsonl` |
| Output | `Stage3Output` | `data/stage3/{accepted,rejected}.jsonl` |

**Invariants:**
* A record never drops `Stage2Output` fields, regardless of `valid`.
* `valid == False` requires at least one entry in `reject_reasons`.
* `quality` fields are optional (`None`) if that check didn't run;
  populate whatever you measured.

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
* `Stage4Sft.messages` is exactly three entries: system / user / assistant
  (system prompt from `configs/stage4/report.yaml`, user = `source_text`,
  assistant = `ko_text`).
* `Stage4Sft.metadata.source_id == Stage3Output.id`.

## Evolution rules

1. **Additive only** across stage boundaries. Never rename a field used by a
   downstream stage — add a new one and deprecate.
2. Bump `nemos_dream.__schema_version__` with every `schemas.py` change.
3. Grep `Stage{1,2,3}Output` across the repo after any edit to verify no
   consumer broke. The `update-schema` skill automates this.
4. Record the change (what, when, why) in a new section at the bottom of
   this file so future teammates understand the delta.

## Changelog

* **v2 (2026-04-21)** — renamed `Stage2Output.ko_text_pre_marker` →
  `ko_text_draft` (more neutral: stage 2's first pass is a translation draft,
  not a marker-specific intermediate). Added `RewriteMeta.extra: dict` to
  honor "Metadata 추가될 수 있음" without future schema churn. No stage
  implementations exist yet, so this is a scaffold-phase rename rather than
  a breaking migration.
