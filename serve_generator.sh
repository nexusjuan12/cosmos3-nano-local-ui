#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv-cosmos3/bin/activate

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

vllm serve nvidia/Cosmos3-Nano \
  --omni \
  --host "${COSMOS3_HOST:-0.0.0.0}" \
  --port "${COSMOS3_PORT:-8000}" \
  --model-class-name Cosmos3OmniDiffusersPipeline \
  --init-timeout "${COSMOS3_INIT_TIMEOUT:-1800}"
