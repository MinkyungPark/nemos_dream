---
name: update-schema
description: Rules for safely evolving `src/nemos_dream/schemas.py`. Invoke whenever the user edits schemas.py, adds a new stage output field, or asks about schema migration.
---

# Updating `schemas.py`

`src/nemos_dream/schemas.py` is the contract. Every stage imports from it —
so a wrong edit breaks every teammate at once.

## The rules

1. **Additive only** across stage boundaries. Never rename, re-type, or
   remove a field that's already in a `Stage{1,2,3}Output`. Add a new
   optional field and deprecate the old one in a follow-up.
2. Bump `nemos_dream.__schema_version__` in `src/nemos_dream/__init__.py`.
   Stage 2 already has an open escape hatch (`RewriteMeta.extra: dict`) —
   use that for ad-hoc metadata rather than bumping the version, unless the
   signal is clearly going to be load-bearing long-term.
3. Update `.claude/docs/stage-contracts.md` — add the new field under its
   stage and document the invariant.
4. Add coverage in `tests/fixtures/sample_rows.py` — every schema field must
   appear in at least one canned fixture. `tests/test_schemas.py` catches
   missing coverage via round-trip.
5. `uv run pytest tests/test_schemas.py` must pass before pushing.

## Checklist before committing a schema change

```bash
# 1. Which consumers exist?
grep -rn "Stage1Output\|Stage2Output\|Stage3Output\|Stage4Sft" src/ tests/

# 2. Did you update the fixture?
grep -n "new_field" tests/fixtures/sample_rows.py

# 3. Did you bump the version?
grep -n "__schema_version__" src/nemos_dream/__init__.py

# 4. Is the round-trip test still green?
uv run pytest tests/test_schemas.py -q

# 5. Did you document it?
grep -n "new_field" .claude/docs/stage-contracts.md
```

If any of those is empty, stop and fix before shipping.

## Allowed changes at a glance

| Change | OK? | Notes |
|---|---|---|
| Add a new field with a default | ✅ | Additive |
| Add a new enum value to an existing `Literal[...]` | ✅ | Prompts must be updated in the same commit |
| Remove an enum value | ⚠️ | Only if no production data has used it — otherwise deprecate instead |
| Rename a field | ❌ | Never across stage boundaries. Intra-stage fields can be renamed. |
| Change a field's type | ❌ | Add a new field, deprecate the old one |
| Make an optional field required | ❌ | Downstream data breaks validation |
| Add a new `Stage{N}Output` subclass | ✅ | Keep layering (inherit from predecessor) |

## When in doubt

Ask in the team channel before editing. Silent schema drift is the single
fastest way to break multi-owner parallel work.
