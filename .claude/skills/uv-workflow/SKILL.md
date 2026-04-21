---
name: uv-workflow
description: Use this skill when the user is adding, syncing, or managing Python dependencies in the nemos_dream repo — any mention of `uv`, `pyproject.toml`, `uv.lock`, a `pip install` request, or a missing module. Handles per-stage optional-extras, base/dev groups, and lockfile regeneration.
---

# uv workflow for nemos_dream

We use uv as the sole Python env manager. Everything lives in a single
package with per-stage optional-extras, so each teammate only pays for the
dependencies they need.

## Mental model

- **Base dependencies** (`[project.dependencies]`): shared by every stage —
  `pydantic`, `openai`, `python-dotenv`, `pyyaml`, `tqdm`, `numpy`, `pandas`.
- **Per-stage extras** (`[project.optional-dependencies]`): `stage1`,
  `stage2`, `stage3`, `stage4`. Stage 3 is by far the heaviest (Curator, NeMo
  ecosystem).
- **Dev group** (`[dependency-groups.dev]`): `pytest`, `ruff`, `mypy`. Always
  installed via the `default-groups = ["dev"]` setting.

## Common commands

| What | Command |
|---|---|
| Fresh install for a single stage owner | `uv sync --extra stage1` |
| Fresh install for the whole pipeline | `uv sync --all-extras` |
| Sync after pulling (picks up new deps) | `uv sync` (preserves extras you previously selected) |
| Add a base dep | `uv add requests` |
| Add a stage-1-only dep | `uv add --optional stage1 some-pkg` |
| Add a dev dep | `uv add --group dev pytest-mock` |
| Remove | `uv remove package-name` |
| Upgrade all | `uv lock --upgrade && uv sync` |
| Run a Python script | `uv run python scripts/run_stage.py ...` |
| Run pytest | `uv run pytest` |

## When to put a dep where

| Dep character | Goes to |
|---|---|
| Used by ≥ 2 stages (e.g. `openai`) | base `[project.dependencies]` |
| Used only by one stage and heavy (e.g. `nemo-curator`) | that stage's extras |
| Used only by tests / linters | `[dependency-groups.dev]` |

If unsure, ask first. Wrong placement is cheap to fix (one edit + `uv sync`),
but putting a 2 GB Curator dep in base would hurt every teammate's install time.

## Lockfile

`uv.lock` is committed. After adding/removing deps the file changes — commit
it alongside the `pyproject.toml` change. Never `uv sync --no-lock`.

## Python version

Pinned to 3.11 via `.python-version`. The cluster's system Python is 3.9 but
`uv sync` will provision a 3.11 `.venv/` automatically. Do not downgrade the
pin — several NVIDIA packages require ≥ 3.10.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` after pulling | `uv sync --all-extras` (or `--extra stageN`) |
| `uv add` complains about python version | `uv python pin 3.11` |
| `uv.lock` conflicts in PR | Prefer regenerating: `rm uv.lock && uv lock` |
| Old `.venv` picked up by the shell | `rm -rf .venv && uv sync` |
