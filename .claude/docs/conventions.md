# Conventions

## Stub-file policy (scaffold phase only)

Every `.py` file outside `src/nemos_dream/schemas.py` is one of:

| Type | Body |
|---|---|
| Empty `__init__.py` | ≤ 1 line module docstring |
| Prompt placeholder | `CONST: str = ""` with explanatory docstring |
| Signature stub | typed signature + docstring + `raise NotImplementedError("stage N owner: implement")` |

`schemas.py` is the only file with real logic — it IS the contract. Stubbing
it would block everyone.

**When you implement a stage**, remove the `raise` and add your own tests
under `tests/stage{N}/`. Layout within your stage is your call; only the
schema contract and the `runner.run(...)` entrypoint are fixed.

## Python style

* Line length 100 (`pyproject.toml::tool.ruff`)
* Target version 3.11 (`.python-version`)
* `from __future__ import annotations` at the top of every module
* Prefer `|` unions over `Union[...]`
* Prefer `list[X]` / `dict[X, Y]` over `typing.List` / `typing.Dict`
* Type-hint every function signature. Internal helpers can skip return
  annotations only when they're pure-local.

## Running

| Task | Command |
|---|---|
| Install base + dev deps | `uv sync` |
| Install one stage | `uv sync --extra stage{1,2,3,4}` |
| Install everything | `uv sync --all-extras` |
| Run tests | `uv run pytest` |
| Run one stage's tests | `uv run pytest tests/stage1/` |
| Lint | `uv run ruff check src/ tests/` |
| Typecheck | `uv run mypy src/` |

## Commit conventions

Prefix commit messages with the stage number when the change is
stage-local: `stage1: implement dict_lookup`. Use `shared:` for
`schemas.py`, `nvidia_clients.py`, `io_utils.py`. Use `infra:` for
`pyproject.toml`, `configs/pipeline.yaml`, CI, or scripts.

## Secrets

`.env` is git-ignored. The full key list is in `.env.example`. Never print
a full API key in a log line — mask to `nvapi-...{last 4}`.

