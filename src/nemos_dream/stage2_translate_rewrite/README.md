# Stage 2 — `translate_rewrite`

> **Owner:** (assign teammate) · **Reference:** draft plan steps 3 + 4.

**Goal.** Turn a `Stage1Output` row into a `Stage2Output`:

1. **번역** — translate the English source text to Korean.
2. **Rewrite (post-processing)** — rewrite the Korean draft conditioned on
   stage-1 metadata (cultural mappings, register, markers, age group, …) and
   any target metadata the owner wants to add.

"Metadata 추가될 수 있음" — the `RewriteMeta` schema is intentionally open;
extend it via its `extra: dict[str, Any]` field when you need to carry new
targeting signals without breaking downstream stages.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input | `Stage1Output` | `data/stage1/*.jsonl` |
| Output | `Stage2Output` | `data/stage2/*.jsonl` |

`Stage2Output` extends `Stage1Output` with `ko_text_draft` (translation
draft), `ko_text` (final rewrite), and `rewrite_meta`.

## Layout (suggested, not enforced)

| File | What goes here |
|---|---|
| `translate.py` | English → Korean draft |
| `rewrite.py` | Korean draft → final Korean SNS post (cultural / marker / register) |
| `prompts.py` | Prompt constants |
| `runner.py` | End-to-end: load → translate → rewrite → write |

Owner is free to fold translate + rewrite into a single LLM call, add a
persona module, or split marker injection out — as long as the schema
contract holds.

## Install + run

```bash
uv sync --extra stage2
uv run python -m scripts.run_stage --stage 2 \
    --input data/stage1/out.jsonl \
    --output data/stage2/out.jsonl
```
