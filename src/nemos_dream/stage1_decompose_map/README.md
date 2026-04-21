# Stage 1 — `decompose_map`

> **Owner:** (assign teammate) · **Reference impl:** `../nemo_dream_step1/` has a working version of most of this stage.

**Goal.** Turn a raw SODA-style multi-turn English dialogue into a
`Stage1Output`:

1. **구조화** — upgrade parallel `dialogue` / `speakers` lists into
   `list[Turn]` and extract per-speaker metadata (`Speaker`) and scene
   context (`Scene`).
2. **사회언어학적 분해** — dialogue-level aggregate (`DialogueDecomposed`):
   overall register, overall emotion, speech acts, cultural references.
3. **문화적 요소 추가** — for each English cultural reference, attach the
   Korean equivalent ("어떤 말이 이 말로 바뀐다").

## Contract

| | Schema (`src/nemos_dream/schemas.py`) | Artifact |
|---|---|---|
| Input | `RawInput` | `data/raw/*.jsonl` |
| Output | `Stage1Output` | `data/stage1/*.jsonl` |

See `data/stage1/example_output.jsonl` for the canonical `Stage1Output`
shape and `data/stage1/example_input.jsonl` for the raw SODA input.

## Layout (suggested, not enforced)

| File | What goes here |
|---|---|
| `decompose.py` | `RawInput` → (`list[Turn]`, `list[Speaker]`, `Scene`, `DialogueDecomposed`) |
| `cultural_map.py` | `list[CulturalRef]` → `list[MappedRef]` |
| `prompts.py` | Any prompt constants you need |
| `runner.py` | End-to-end: load → decompose → map → write |

You can split these further, merge them, or pick a different backend (Data
Designer, direct NIM, NAT/ReAct agent, …) — what matters is the I/O contract
above.

## Useful NVIDIA stack

See `.claude/docs/nvidia-stack.md` for the full table. Candidates commonly
used here: Nemotron (NIM), NeMo Data Designer, NeMo Retriever, NeMo Agent
Toolkit, Tavily.

## Install + run

```bash
uv sync
uv run python -m scripts.run_stage --stage 1 \
    --input data/raw/sample_input.jsonl \
    --output data/stage1/out.jsonl
```
