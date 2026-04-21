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
* `len(mapped_refs) == len(decomposed.cultural_refs)` (every ref gets a mapping,
  even if `source='web+llm'` with a low-confidence `notes`).
* `internet_markers.laughter` ∈ {lol, lmao, rofl, haha, none}; the LLM must
  pick `none` if uncertain — never infer.

## Stage 2 — `stage2_rewrite_marker`

| | Schema | Location |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

**Invariants:**
* All `Stage1Output` fields are preserved verbatim — do **not** re-run
  decomposition or cultural mapping.
* `ko_text_pre_marker` is the LLM output before marker injection;
  `ko_text` is the post-marker final text.
* For every `MappedRef` where `source != 'web+llm' or retrieved == False`,
  the `ko` string should appear in `ko_text` (soft rule — stage 3 R5 enforces
  it strictly).

## Stage 3 — `stage3_validate_filter`

| | Schema | Location |
|---|---|---|
| Input | `Stage2Output` | `data/stage2/*.jsonl` |
| Output | `Stage3Output` | `data/stage3/{accepted,rejected}.jsonl` |

**Invariants:**
* A record never drops `Stage2Output` fields, regardless of `valid`.
* `valid == False` requires at least one entry in `reject_reasons`.
* `quality` fields are optional (`None`) only if that stage failed before
  measuring them; otherwise populate.

**Reject semantics:** stages S2..S6 should call `record.reject(stage=..., rule=..., detail=...)`
rather than raising. Exceptions are reserved for infrastructure failures
(network, schema parse errors) that belong in logs, not the output artifact.

## Stage 4 — `stage4_report_viz`

| | Schema | Location |
|---|---|---|
| Input (accepted) | `Stage3Output` | `data/stage3/accepted.jsonl` |
| Input (rejected) | `Stage3Output` | `data/stage3/rejected.jsonl` |
| Output (SFT) | `Stage4Sft` | `data/reports/sft.jsonl` |
| Output (report) | — | `data/reports/report.html`, `.json` |

**Invariants:**
* `Stage4Sft.messages` is always exactly three entries: system / user / assistant.
  System = `configs/stage4/report.yaml::sft.system_prompt`, user = `source_text`,
  assistant = `ko_text`.
* `Stage4Sft.metadata.source_id == Stage3Output.id`.

## Evolution rules

1. **Additive only** across stage boundaries. Never rename a field used by a
   downstream stage — add a new one and deprecate.
2. Bump `nemos_dream.__schema_version__` with every `schemas.py` change.
3. Grep `Stage{1,2,3}Output` across the repo after any edit to verify no
   consumer broke. The `update-schema` skill automates this.
4. Record the change (what, when, why) in a new section at the bottom of
   this file so future teammates understand the delta.
