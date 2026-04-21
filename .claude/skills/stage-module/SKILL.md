---
name: stage-module
description: Use this skill when the user is implementing or modifying code inside one of the four stage subpackages — `stage1_decompose_map`, `stage2_rewrite_marker`, `stage3_validate_filter`, or `stage4_report_viz`. Enforces the contract-first convention, the factory pattern for NVIDIA clients, and the stage-local runner entrypoint.
---

# Implementing code in a stage subpackage

Before writing any code, read these in this order:

1. `src/nemos_dream/schemas.py` — the Pydantic contract.
2. The target stage's `README.md` — input/output + NVIDIA tool map.
3. `.claude/docs/stage-contracts.md` — invariants for the stage you're editing.
4. The matching reference repo:
   - Stage 1 → `../nemo_dream_step1/`
   - Stage 3 → `../nemotron-test/`
   - Stages 2, 4 → no reference; design from `draft_plan.md`.

## Rules

1. **Never widen the inter-stage contract ad-hoc.** If you need a new field,
   load the `update-schema` skill first. Adding `record.custom = ...` to get
   unstuck will silently break every downstream stage.

2. **Use the factories in `nvidia_clients.py`.** Do not instantiate
   `OpenAI()` / `AsyncOpenAI()` directly. If a factory is missing, add it —
   that's a `shared owner` change, but it's the right place.

3. **Runner pattern.** Every stage has a `runner.py` with a single `run(...)`
   entrypoint. Scripts in `scripts/` dispatch to these runners. Individual
   helpers inside the stage are not called from outside the subpackage.

4. **Per-row methods return Pydantic models.** Never return bare dicts from
   stage-internal functions — it defeats the whole contract.

5. **When you implement a function, remove its `xfail` in the matching
   `tests/stage{N}/*.py`** in the same commit.

6. **Stay in your stage.** Don't edit another stage's code or configs.
   Schema changes go through `update-schema`.

## Imports

- From the shared root: `from nemos_dream.schemas import Stage1Output, ...`
- From the stage itself (internal): `from .cultural_map import map_refs`
  (relative import within the subpackage)

## Testing locally

```bash
uv sync --extra stage1   # (or the stage you own)
uv run pytest tests/stage1/ -v
uv run ruff check src/nemos_dream/stage1_decompose_map/
```

If stage 3's Curator deps conflict with your environment, fall back to the
lightweight orchestrator (`runner.run(..., mode='lightweight')`) — it doesn't
need Curator and is still end-to-end-correct for dev iteration.

## Error handling

Infrastructure failures (HTTP, schema parse) **raise**. Data-level rejections
(safety/PII/rules) **set `valid=False` + append a `RejectReason`**. Don't
mix the two — a judge timeout is not a rejection.
