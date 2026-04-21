# Stage 1 — `decompose_map`

> **Owner:** (assign teammate)
> **Reference impl:** `../nemo_dream_step1/` — most of this subpackage can be lifted as-is.

Converts raw English SNS posts into `Stage1Output` rows: sociolinguistic metadata
(speech act, register, emotion, …) **plus** Korean mappings for every cultural
reference found in the source text.

## Contract

| | Schema (`src/nemos_dream/schemas.py`) | Artifact |
|---|---|---|
| Input | `RawInput` | `data/raw/*.jsonl` |
| Output | `Stage1Output` | `data/stage1/*.jsonl` |

See `data/stage2/example.jsonl` for a real-world example of this shape
(naming note: in the reference repo it was called "stage 1+2 combined").

## Pipeline

```
RawInput
  ├─ decompose.py       # NeMo Data Designer (primary) / NIM guided_json (fallback)
  └─ cultural_map.py    # dict → retriever → web+llm chain
       └─ tools/
            ├─ dict_lookup.py        # configs/stage1/cultural_map_seed.json
            ├─ retriever_search.py   # NeMo Retriever (embedqa)
            └─ web_search.py         # Tavily + Nemotron reasoning
```

## NVIDIA stack

| Path | Tool | Model |
|---|---|---|
| Primary extraction | **NeMo Data Designer** | `nvidia/nemotron-3-nano-30b-a3b` |
| Fallback extraction | **NIM** + `nvext.guided_json` (XGrammar) | same |
| Semantic retrieval | **NeMo Retriever** | `nvidia/llama-3.2-nv-embedqa-1b-v2` |
| Agentic mapping (opt-in, `MAP_REFS_USE_NAT=1`) | **NeMo Agent Toolkit** | Nemotron nano |
| Web-grounded reasoning | **NIM** + guided_json | Nemotron nano |

## Install

```bash
uv sync --extra stage1
```

## Run

```bash
uv run python -m scripts.run_stage --stage 1 \
    --input data/raw/sample_input.jsonl \
    --output data/stage1/out.jsonl
```
