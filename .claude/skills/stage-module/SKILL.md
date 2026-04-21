---
name: stage-module
description: Use this skill when the user is implementing or modifying code inside one of the four stage subpackages — `stage1_decompose_map`, `stage2_translate_rewrite`, `stage3_validate`, or `stage4_report`. Enforces the contract-first convention, the factory pattern for NVIDIA clients, and the stage-local runner entrypoint.
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
   load the `update-schema` skill first. Stage 2 has an escape hatch
   (`RewriteMeta.extra: dict`) for ad-hoc targeting signals — prefer that
   over bolting new top-level fields onto the schema.

2. **Use the factories in `nvidia_clients.py`.** Do not instantiate
   `OpenAI()` / `AsyncOpenAI()` directly. If a factory is missing, add it —
   that's a `shared owner` change, but it's the right place.

3. **Runner pattern.** Every stage has a `runner.py` with a single `run(...)`
   entrypoint. Scripts in `scripts/` dispatch to these runners. You're free
   to split internal modules however you like — the only locked surface is
   the schema contract and `runner.run(...)`.

4. **Per-row methods return Pydantic models.** Never return bare dicts from
   stage-internal functions that cross the stage boundary — it defeats the
   contract.

5. **Stay in your stage.** Don't edit another stage's code or configs.
   Schema changes go through `update-schema`.

## Imports

- From the shared root: `from nemos_dream.schemas import Stage1Output, ...`
- From within the stage: `from .cultural_map import map_refs`
  (relative import within the subpackage).

## Testing locally

```bash
uv sync --extra stage1        # (or the stage you own)
uv run pytest tests/          # schema round-trip must always pass
uv run ruff check src/nemos_dream/stage1_decompose_map/
```

Stage owners add their own tests under `tests/stage{N}/` when they start
implementing.

## Error handling

Infrastructure failures (HTTP, schema parse) **raise**. Data-level rejections
(safety / PII / rules) **set `valid=False` + append a `RejectReason`**. Don't
mix the two — a judge timeout is not a rejection.
