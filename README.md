# nemos_dream

> **NVIDIA Nemotron Hackathon 2026 — Track C (SDG).**
> English SNS datasets → Korean datasets for k-sovereign LLM training.
> **Not translation — cultural rewriting.**

This repo is a 4-stage synthetic-data-generation pipeline with one teammate
per stage. Stages share a single Pydantic contract (`src/nemos_dream/schemas.py`)
and layered JSONL artifacts under `data/stage{N}/`.

## Pipeline

```
┌──────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────┐
│  RawInput    │ → │ Stage 1            │ → │ Stage 2            │ → │ Stage 3            │ → │ Stage 4        │
│  (EN SNS)    │   │ decompose + map    │   │ rewrite + marker   │   │ validate + filter  │   │ report + SFT   │
│ data/raw/    │   │ data/stage1/       │   │ data/stage2/       │   │ data/stage3/       │   │ data/reports/  │
└──────────────┘   └───────────────────┘   └───────────────────┘   └───────────────────┘   └───────────────┘
                    nemo_dream_step1 ref    new                     nemotron-test ref       new
```

| Stage | Package | Owner | Input schema | Output schema |
|---|---|---|---|---|
| 1 | `stage1_decompose_map` | TBD | `RawInput` | `Stage1Output` |
| 2 | `stage2_rewrite_marker` | TBD | `Stage1Output` | `Stage2Output` |
| 3 | `stage3_validate_filter` | TBD | `Stage2Output` | `Stage3Output` |
| 4 | `stage4_report_viz` | TBD | `Stage3Output` | `Stage4Sft` + report.html |

See `.claude/docs/architecture.md` for the full data-flow, `.claude/docs/stage-contracts.md`
for the schema contract per boundary, and each stage's `README.md` for owner-level detail.

## Quickstart

```bash
# 0. Clone, then copy env template
cp .env.example .env
# Edit .env: set NVIDIA_API_KEY (build.nvidia.com) and TAVILY_API_KEY

# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install the stages you're working on
uv sync --extra stage1            # stage 1 owner
uv sync --extra stage2            # stage 2 owner
uv sync --extra stage3            # stage 3 owner
uv sync --extra stage4            # stage 4 owner
uv sync --all-extras              # run the whole pipeline

# 3. Run tests — the schema round-trip test must pass.
# All stage-specific tests are xfail until that stage is implemented.
uv run pytest

# 4. Run a single stage
uv run python scripts/run_stage.py --stage 1 \
    --input data/raw/sample_input.jsonl \
    --output data/stage1/out.jsonl

# 5. End-to-end run
uv run python scripts/run_pipeline.py --input data/raw/sample_input.jsonl
```

On the Slurm cluster use `scripts/slurm/run_stage{N}.sbatch` wrappers instead.
Login-node-safe — every sbatch job goes to partition `cpu` (API-only workload).

## NVIDIA stack at a glance

| Stage | NVIDIA tools |
|---|---|
| 1 | NIM · NeMo Data Designer · NeMo Retriever · (opt) NeMo Agent Toolkit |
| 2 | NIM · HF `Nemotron-Personas-Korea` |
| 3 | NeMo Curator · NeMoGuard · NIM (70B judge) · Nemotron-4-340B-Reward |
| 4 | (none — pure analysis) |

Full model IDs, env vars, and endpoints: `.claude/docs/nvidia-stack.md`.

## Repo layout

```
nemos_dream/
├── pyproject.toml              uv-managed, per-stage optional-deps
├── configs/                    pipeline.yaml + stage{1..4}/*.yaml
├── data/                        raw/ + stage{1,2,3}/ + reports/
├── src/nemos_dream/
│   ├── schemas.py               ★ canonical contract (the only file with real logic)
│   ├── io_utils.py              shared JSONL / HF loaders
│   ├── nvidia_clients.py        NIM / Retriever / judge / safety / reward client factories
│   ├── proxy_patch.py           corp-proxy monkey-patch
│   ├── stage1_decompose_map/    …
│   ├── stage2_rewrite_marker/   …
│   ├── stage3_validate_filter/  …
│   └── stage4_report_viz/       …
├── scripts/                     run_stage.py, run_pipeline.py, slurm/*.sbatch
└── tests/                       schema round-trip + xfail-stub tests per stage
```

## What's implemented right now

**Structure, not logic.** Every `.py` file outside `schemas.py` is a
signature stub that raises `NotImplementedError`. The reason: four teammates
can clone this repo today and start filling in their stage in parallel
without blocking on each other.

The schema contract (`schemas.py`) and the test fixtures
(`tests/fixtures/sample_rows.py`) are real — `uv run pytest
tests/test_schemas.py` passes on a fresh clone.

See `.claude/docs/conventions.md` for the stub-file policy.

## License & attribution

Code structure adapts two practice repos from the same team:

- `../nemo_dream_step1/` — stages 1+2 reference implementation
- `../nemotron-test/` — stage 3 reference implementation
