#!/bin/bash
#SBATCH --job-name=nd-install
#SBATCH --partition=cpu
#SBATCH --time=00:15:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs
cd "$SLURM_SUBMIT_DIR"

# uv creates .venv/ at python 3.11 (system python may be 3.9).
uv sync --all-extras
