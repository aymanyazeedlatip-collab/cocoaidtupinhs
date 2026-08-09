#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export PORT="${PORT:-10000}"

if [[ -n "${PERSISTENT_DATA_DIR:-}" ]]; then
  mkdir -p "$PERSISTENT_DATA_DIR"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
