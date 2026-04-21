# Instructions for Claude assistants working in this repo

This is `nemos_dream` — a 4-stage EN→KR cultural SDG pipeline for NVIDIA
Nemotron Hackathon Track C. Four teammates own one stage each.

## Orientation

Before doing anything else, read these in order:

1. `README.md` — pipeline overview
2. `.claude/docs/architecture.md` — data flow + owner map
3. `.claude/docs/stage-contracts.md` — schema at each stage boundary
4. `src/nemos_dream/schemas.py` — the actual Pydantic contract
5. The `README.md` inside the stage subpackage you're editing

## Scaffold-phase ground rules

As of this scaffold, every `.py` file outside `schemas.py` is a signature
stub. Do not add implementation into unrelated stages while working on one —
that couples owners and defeats the per-stage extras split.

## When you change code

- **Editing `schemas.py`:** load the `update-schema` skill. Inter-stage fields
  are additive-only; bump `nemos_dream.__schema_version__`.
- **Implementing a stage:** load the `stage-module` skill. Use the factories
  in `nvidia_clients.py`; don't instantiate `OpenAI()` ad-hoc.
- **Calling NIM for the first time:** load the `nvidia-nim-call` skill.
- **Dependency changes:** load the `uv-workflow` skill. Add deps under the
  right `[project.optional-dependencies]` group, not the base list.

## Testing

`uv run pytest tests/test_schemas.py` must always pass. Stage-specific tests
are `xfail` until that stage is implemented — when you implement a stage,
remove the `xfail` marker from its tests.

## Secrets

Never commit `.env`. `NVIDIA_API_KEY` and `TAVILY_API_KEY` come from
build.nvidia.com / tavily.com and are local-only.
