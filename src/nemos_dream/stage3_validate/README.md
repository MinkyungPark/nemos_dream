# Stage 3 — `validate`

> **Owner:** (assign teammate) · **Reference impl:** `../nemotron-test/` has a working 6-stage Curator pipeline that can be lifted wholesale.

**Goal.** Consume `Stage2Output` rows and decide which ones are good enough
to keep. Attach per-row `QualityScores` and `RejectReason[]`, then split the
stream into `accepted.jsonl` and `rejected.jsonl`.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input | `Stage2Output` | `data/stage2/*.jsonl` |
| Output | `Stage3Output` | `data/stage3/accepted.jsonl`, `rejected.jsonl` |

The schema gives you a full `QualityScores` slot (semantic cosine, four 1–5
rubric axes, safety / PII flags, aggregate, reward). Fill what you use; leave
the rest `None`.

## Layout

Totally up to the owner. `runner.py` is the single required entrypoint. You
can factor internal checks however you like — a 6-stage Curator pipeline, a
flat sequential validator, a Hydra-driven graph, etc. Configs live under
`configs/stage3/`.

## Useful NVIDIA stack

See `.claude/docs/nvidia-stack.md`. Candidates: NeMo Curator, NeMoGuard,
Nemotron-70B judge via NIM, NV-Embed for dedup, Nemotron-4-340B-Reward.

## Install + run

```bash
uv sync
uv run python -m scripts.run_stage --stage 3 \
    --input data/stage2/out.jsonl \
    --output-dir data/stage3/
```
