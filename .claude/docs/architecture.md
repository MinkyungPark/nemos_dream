# Architecture

Four-stage EN→KR cultural SDG pipeline. Each stage is an owned Python
subpackage under `src/nemos_dream/` and consumes its predecessor's JSONL
artifact under `data/stage{N}/`.

## Data flow

```
  data/raw/sample_input.jsonl        (RawInput)
             │
             ▼
  ┌──────────────────────────┐
  │  Stage 1                 │
  │  stage1_decompose_map/   │
  │   • decompose.py         │  Data Designer (primary) / NIM guided_json
  │   • cultural_map.py      │  dict → retriever → web+llm
  └──────────────────────────┘
             │
             ▼
  data/stage1/out.jsonl              (Stage1Output)
             │
             ▼
  ┌──────────────────────────┐
  │  Stage 2                 │
  │  stage2_rewrite_marker/  │
  │   • personas.py          │  pick KR persona (Nemotron-Personas-Korea)
  │   • rewrite.py           │  metadata-conditioned KR rewrite
  │   • markers.py           │  deterministic ㅋㅋ/ㅠㅠ/emoji injection
  └──────────────────────────┘
             │
             ▼
  data/stage2/out.jsonl              (Stage2Output)
             │
             ▼
  ┌──────────────────────────┐
  │  Stage 3                 │
  │  stage3_validate_filter/ │
  │   S1 schema              │  Pydantic + Curator DocumentDataset
  │   S2 rules               │  R1–R7 heuristics
  │   S3 safety              │  NeMoGuard content + PII + jailbreak
  │   S4 semantic            │  back-translation cosine + LLM judge
  │   S5 dedup               │  Exact / Fuzzy / Semantic via Curator
  │   S6 reward              │  Nemotron-4-340B-Reward
  └──────────────────────────┘
             │
             ▼
  data/stage3/{accepted,rejected}.jsonl  (Stage3Output)
             │
             ▼
  ┌──────────────────────────┐
  │  Stage 4                 │
  │  stage4_report_viz/      │
  │   • metrics.py           │  pass rate, reject-reason top-N
  │   • distribution.py      │  register/platform/age histograms
  │   • visualize.py         │  matplotlib + plotly charts
  │   • sft_export.py        │  → OAI-chat Stage4Sft rows
  └──────────────────────────┘
             │
             ▼
  data/reports/{report.html,report.json,sft.jsonl}
```

## Owner map

| Stage | Package | Owner |
|---|---|---|
| 1 | `stage1_decompose_map` | TBD — reference: `../nemo_dream_step1/` |
| 2 | `stage2_rewrite_marker` | TBD — new |
| 3 | `stage3_validate_filter` | TBD — reference: `../nemotron-test/` |
| 4 | `stage4_report_viz` | TBD — new |

## Contract-first discipline

Every inter-stage field lives in `src/nemos_dream/schemas.py`. Stages read
and write only the canonical models. Per-stage YAML configs under
`configs/stage{N}/` hold thresholds and model names — never row shapes.

## Why layered schemas?

`Stage2Output` is a Pydantic subclass of `Stage1Output`, and so on. This
means:

* Every stage can validate its own output against a stricter schema **and**
  re-validate it against earlier schemas (see `tests/test_schemas.py::test_stage_layering`).
* Downstream stages never lose upstream fields — a stage-4 SFT export can
  still reach all the way back to the original `source_text`.
* Adding a new field to stage 2 never breaks stage 3's input validation.
