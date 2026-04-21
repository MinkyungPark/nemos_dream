# Stage 3 — `validate_filter`

> **Owner:** (assign teammate)
> **Reference impl:** `../nemotron-test/` — the 6-stage pipeline and judge
> protocol can be lifted wholesale.

Consumes `Stage2Output` rows, runs them through six validation stages, and
produces `Stage3Output` (same row + `quality`, `valid`, `reject_reasons`).

## Contract

| | Schema | Artifact |
|---|---|---|
| Input | `Stage2Output` | `data/stage2/*.jsonl` |
| Output | `Stage3Output` | `data/stage3/accepted.jsonl`, `rejected.jsonl` |

## Stage layout

| # | Module | Check |
|---|---|---|
| S1 | `stages/s1_schema.py` | Pydantic round-trip against `Stage2Output` |
| S2 | `stages/s2_rules.py` | R1–R7 rule checks (laughter/register/length/emoji) |
| S3 | `stages/s3_safety.py` | NeMoGuard content-safety + PII (regex + Presidio) |
| S4 | `stages/s4_semantic.py` | Back-translation cosine + LLM judge (4 axes) |
| S5 | `stages/s5_dedup.py` | Curator `ExactDuplicates` + `FuzzyDuplicates` + `SemanticDedup` |
| S6 | `stages/s6_reward.py` | `nvidia/nemotron-4-340b-reward` final ranking |

All six share the base class in `stages/base.py`.

## NVIDIA stack

| Path | Tool | Model |
|---|---|---|
| Orchestration | **NeMo Curator** (`Pipeline`, `RayActorPoolExecutor`) | — |
| Safety | **NeMoGuard** (via NIM) | `nvidia/llama-3.1-nemoguard-8b-content-safety` |
| PII | Presidio (regex) + `InstructionDataGuardClassifier` | — |
| LLM judge | **NIM** | `nvidia/llama-3.1-nemotron-70b-instruct` |
| Semantic dedup | `SemanticDedup` | `nvidia/nv-embedqa-e5-v5` |
| Reward | **NIM** | `nvidia/nemotron-4-340b-reward` |

Thresholds and weights live in `configs/stage3/filter.yaml`.

## Install

```bash
uv sync --extra stage3
```

## Run

```bash
uv run python -m scripts.run_stage --stage 3 \
    --input data/stage2/out.jsonl \
    --output-dir data/stage3/

# Hydra: swap judge backend
uv run python -m nemos_dream.stage3_validate_filter.runner \
    judge=mock paths.candidates=data/stage2/out.jsonl
```
