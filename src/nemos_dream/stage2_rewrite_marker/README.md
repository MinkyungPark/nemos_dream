# Stage 2 — `rewrite_marker`

> **Owner:** (assign teammate)
> **Reference:** draft plan steps 3 + 4; no practice repo yet — this is net-new.

Takes a `Stage1Output` row and rewrites the English source into a Korean SNS
post that (a) preserves the sociolinguistic metadata, (b) substitutes the
cultural refs per `mapped_refs`, and (c) injects internet markers (`ㅋㅋ`,
`ㅎㅎ`, `ㅠㅠ`, emoji) deterministically from a rule table.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

`Stage2Output` extends `Stage1Output` with `ko_text`, `ko_text_pre_marker`, and
`rewrite_meta` (`target_platform`, `target_age_group`, `target_community`,
`target_gender_style`, `persona_id`).

## Pipeline

```
Stage1Output
  ├─ personas.py    # pick Korean persona (Nemotron-Personas-Korea) for style scale-up
  ├─ rewrite.py     # LLM: conditioned rewrite (NO translation, NO markers yet)
  └─ markers.py     # deterministic rule-based marker injection post-step
```

**Why separate the LLM rewrite from marker injection?** The draft plan calls it
explicitly — the LLM produces clean Korean body text; the marker step is a
pure function of `InternetMarkers` metadata and `intensity`, so keeping it
rule-based makes the output reproducible and testable.

## NVIDIA stack

| Path | Tool | Model |
|---|---|---|
| Rewriting | **NIM** (chat.completions) | `nvidia/nemotron-3-nano-30b-a3b` (or `super-120b` for final pass) |
| Personas dataset | HF | `nvidia/Nemotron-Personas-Korea` |
| Marker injection | pure-Python rules | — |

## Install

```bash
uv sync --extra stage2
```

## Run

```bash
uv run python -m scripts.run_stage --stage 2 \
    --input data/stage1/out.jsonl \
    --output data/stage2/out.jsonl
```
