# Stage 4 — `report`

> **Owner:** (assign teammate) · **Reference impl:** none — net-new.

**Goal.** Take the stage-3 output streams and produce (a) a human-readable
report (quality distribution, rejection analysis, whatever the owner finds
useful) and (b) the final SFT JSONL in OpenAI-chat shape.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input (accepted) | `Stage3Output` | `data/stage3/accepted.jsonl` |
| Input (rejected) | `Stage3Output` | `data/stage3/rejected.jsonl` |
| Output (report) | — | `data/reports/report.{html,json,…}` |
| Output (SFT) | `Stage4Sft` | `data/reports/sft.jsonl` |

See `data/reports/example_sft.json` for one row of the target SFT shape.

## Layout

Up to the owner. `runner.py` is the single required entrypoint. Add
submodules (metrics, viz, export, …) as you see fit. Configs live under
`configs/stage4/`.

## Install + run

```bash
uv sync --extra stage4
uv run python -m scripts.run_stage --stage 4 \
    --accepted data/stage3/accepted.jsonl \
    --rejected data/stage3/rejected.jsonl \
    --output-dir data/reports/
```
