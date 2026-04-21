# Stage 1 — `decompose_map`

> **Owner:** (assign teammate) · **Reference impl:** `../nemo_dream_step1/` has a working version of most of this stage.

**Goal.** Turn a raw English SNS post into a `Stage1Output`:

1. **사회언어학적 분해** — extract speech act, register, emotion, internet
   markers, age-group hint, platform fit, and cultural references.
2. **문화적 요소 추가** — for each English cultural reference, attach the
   Korean equivalent ("어떤 말이 이 말로 바뀐다").

## Contract

| | Schema (`src/nemos_dream/schemas.py`) | Artifact |
|---|---|---|
| Input | `RawInput` | `data/raw/*.jsonl` |
| Output | `Stage1Output` | `data/stage1/*.jsonl` |

See `data/stage2/example.jsonl` for a real-world example of the final
`Stage1Output` shape (the reference repo called this "stage 1+2 combined").

## Layout (suggested, not enforced)

| File | What goes here |
|---|---|
| `decompose.py` | `RawInput` → `Decomposed` |
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
uv sync --extra stage1
uv run python -m scripts.run_stage --stage 1 \
    --input data/raw/sample_input.jsonl \
    --output data/stage1/out.jsonl
```
