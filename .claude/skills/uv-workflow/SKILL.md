---
name: uv-workflow
description: Use this skill when the user is adding, syncing, or managing Python dependencies in the nemos_dream repo — any mention of `uv`, `pyproject.toml`, `uv.lock`, a `pip install` request, or a missing module. Handles the flat dependency list, dev group, and lockfile regeneration.
---

# uv workflow for nemos_dream

We use uv as the sole Python env manager. Dependencies are a single flat
list — base Python libs + NVIDIA Nemotron stack. No per-stage extras.

## Mental model

- **Project dependencies** (`[project.dependencies]`): everything every stage
  can use. Base libs (`pydantic`, `openai`, `python-dotenv`, `pyyaml`, `tqdm`,
  `numpy`, `pandas`) + NVIDIA stack (`data-designer`, `nvidia-nat[langchain]`,
  `nemo-curator`, `langchain-nvidia-ai-endpoints`, `datasets` for HF).
- **Dev group** (`[dependency-groups.dev]`): `pytest`, `ruff`, `mypy`. Always
  installed via the `default-groups = ["dev"]` setting.

## Common commands

| What | Command |
|---|---|
| Install everything | `uv sync` |
| Add a dep | `uv add some-pkg` |
| Add a dev dep | `uv add --group dev pytest-mock` |
| Remove | `uv remove some-pkg` |
| Upgrade all | `uv lock --upgrade && uv sync` |
| Run a script | `uv run python scripts/run_stage.py ...` |
| Run pytest | `uv run pytest` |

## When to add a dep

Keep the list tight. Only add if:

1. The package is part of the NVIDIA Nemotron stack (NeMo, Curator, NIM,
   Retriever, Agent Toolkit, NeMoGuard, …), **or**
2. It's a genuinely foundational library every stage could use (Pydantic,
   OpenAI SDK, pandas, …).

Stage-specific single-use libs (plotting, web search, PII regex, …) should
be evaluated carefully — prefer standard-library or existing deps first. If
a one-off dep is truly needed, just add it to the flat list; per-stage
extras were removed on purpose.

## Lockfile

`uv.lock` is committed. After adding/removing deps, commit the lock change
alongside the `pyproject.toml` change. Never `uv sync --no-lock`.

## Python version

Pinned to 3.11 via `.python-version`. `uv sync` auto-provisions a 3.11
`.venv/`. Do not downgrade — several NVIDIA packages require ≥ 3.10.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` after pulling | `uv sync` |
| `uv add` complains about python version | `uv python pin 3.11` |
| `uv.lock` conflicts in PR | Prefer regenerating: `rm uv.lock && uv lock` |
| Old `.venv` picked up by the shell | `rm -rf .venv && uv sync` |
