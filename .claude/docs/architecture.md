# Architecture

Four-stage EN→KR cultural SDG pipeline. Each stage is an owned Python
subpackage under `src/nemos_dream/` and consumes its predecessor's JSONL
artifact under `data/stage{N}/`.

## Data flow

```
  data/raw/sample_input.jsonl              (RawInput)
             │
             ▼
  ┌──────────────────────────────┐
  │  Stage 1                     │
  │  stage1_decompose_map/       │
  │   • decompose.py             │  사회언어학적 분해
  │   • cultural_map.py          │  문화적 요소 추가 ("어떤 말이 이 말로 바뀐다")
  └──────────────────────────────┘
             │
             ▼
  data/stage1/out.jsonl                    (Stage1Output)
             │
             ▼
  ┌──────────────────────────────┐
  │  Stage 2                     │
  │  stage2_translate_rewrite/   │
  │   • translate.py             │  EN → KR draft
  │   • rewrite.py               │  post-processing rewrite
  │                              │  (cultural / register / markers;
  │                              │   RewriteMeta.extra holds ad-hoc metadata)
  └──────────────────────────────┘
             │
             ▼
  data/stage2/out.jsonl                    (Stage2Output)
             │
             ▼
  ┌──────────────────────────────┐
  │  Stage 3                     │
  │  stage3_validate/            │
  │   runner.py — owner's choice │  schema / rules / safety / dedup / judge / reward
  └──────────────────────────────┘
             │
             ▼
  data/stage3/{accepted,rejected}.jsonl    (Stage3Output)
             │
             ▼
  ┌──────────────────────────────┐
  │  Stage 4                     │
  │  stage4_report/              │
  │   runner.py — owner's choice │  metrics / viz / SFT export
  └──────────────────────────────┘
             │
             ▼
  data/reports/{report.*,sft.jsonl}
```

## Owner map

| Stage | Package | Owner |
|---|---|---|
| 1 | `stage1_decompose_map` | TBD — reference: `../nemo_dream_step1/` |
| 2 | `stage2_translate_rewrite` | TBD — new |
| 3 | `stage3_validate` | TBD — reference: `../nemotron-test/` |
| 4 | `stage4_report` | TBD — new |

## Contract-first discipline

Every inter-stage field lives in `src/nemos_dream/schemas.py`. Stages read
and write only the canonical models. Per-stage YAML configs under
`configs/stage{N}/` hold thresholds and model names — never row shapes.

Within a stage, the owner has free rein: add submodules, split runners,
swap backends. Only the stage boundary (the Pydantic schema + the
`data/stage{N}/` JSONL artifact) is locked.

## Why layered schemas?

`Stage2Output` is a Pydantic subclass of `Stage1Output`, and so on. This
means:

* Every stage can validate its own output against a stricter schema **and**
  re-validate it against earlier schemas (see
  `tests/test_schemas.py::test_stage_layering`).
* Downstream stages never lose upstream fields — a stage-4 SFT export can
  still reach all the way back to the original `source_text`.
* Adding a new field to stage 2 never breaks stage 3's input validation.
* `RewriteMeta.extra` (dict) lets stage 2 ship ad-hoc targeting signals
  without a schema bump; promote repeat keys to real fields once they stick.
