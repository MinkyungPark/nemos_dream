#!/bin/bash
#SBATCH --job-name=nd-stage2
#SBATCH --partition=cpu
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs
cd "$SLURM_SUBMIT_DIR"

uv run python scripts/run_stage.py --stage 2 "$@"
