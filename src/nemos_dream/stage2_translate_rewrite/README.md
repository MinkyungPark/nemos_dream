# Stage 2 — `translate_rewrite`

> **Owner:** (assign teammate) · **Reference:** draft plan steps 3 + 4.

**Goal.** Turn a `Stage1Output` row into a `Stage2Output`:

1. **번역** — translate the English dialogue to Korean, turn by turn
   (→ `korean_dialogue_draft`).
2. **Rewrite (post-processing)** — rewrite each Korean turn conditioned on
   stage-1 metadata (`scene`, `dialogue_decomposed`, `mapped_refs`) plus a
   per-speaker `Persona` (성별/나이/직업/학력/결혼여부/군대여부/가족형태/
   집주거여부/전공) and `Style` (격식체/감정/마커/말하는스타일) overlay
   (→ `korean_dialogue`).

Ad-hoc per-run metadata (target platform, community, sampling pass, …) goes
in `Stage2Output.translation_meta` (open dict) — no schema bump required
until a key is clearly load-bearing long-term.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

`Stage2Output` extends `Stage1Output` with `korean_dialogue_draft`
(translation draft), `korean_dialogue` (final rewrite),
`speaker_personas`, `speaker_styles`, and `translation_meta`.

## Layout (suggested, not enforced)

| File | What goes here |
|---|---|
| `translate.py` | English dialogue → Korean turn draft |
| `rewrite.py` | Korean draft + persona + style → final Korean dialogue |
| `prompts.py` | Prompt constants |
| `runner.py` | End-to-end: load → translate → rewrite → write |

Owner is free to fold translate + rewrite into a single LLM call, add a
persona sampler module, or split marker injection out — as long as the
schema contract holds.

## Install + run

```bash
uv sync
uv run python -m scripts.run_stage --stage 2 \
    --input data/stage1/out.jsonl \
    --output data/stage2/out.jsonl
```
