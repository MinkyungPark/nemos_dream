# Stage 4 — `report_viz`

> **Owner:** (assign teammate)
> **Reference impl:** none — net-new.

Turns stage-3 `accepted.jsonl` / `rejected.jsonl` into a human-readable
report (metrics, distributions, rejection analysis) and exports the final
SFT rows in OpenAI-chat shape.

## Contract

| | Schema | Artifact |
|---|---|---|
| Input (accepted) | `Stage3Output` | `data/stage3/accepted.jsonl` |
| Input (rejected) | `Stage3Output` | `data/stage3/rejected.jsonl` |
| Output (report) | — | `data/reports/report.{html,json}` |
| Output (SFT) | `Stage4Sft` | `data/reports/sft.jsonl` |

See `data/reports/example_sft.json` for one row of the target SFT shape.

## Modules

| Module | Responsibility |
|---|---|
| `metrics.py` | Aggregate quality axes, pass rate, reject-reason top-N |
| `distribution.py` | Histograms over `register`, `platform`, `age_group`, `speech_act` |
| `visualize.py` | matplotlib / plotly charts → PNG + HTML |
| `sft_export.py` | `Stage3Output` → `Stage4Sft` (OAI-chat messages + metadata) |
| `runner.py` | Orchestrates the above; renders `templates/report.html.j2` |

## Install

```bash
uv sync --extra stage4
```

## Run

```bash
uv run python -m scripts.run_stage --stage 4 \
    --accepted data/stage3/accepted.jsonl \
    --rejected data/stage3/rejected.jsonl \
    --output-dir data/reports/
```
