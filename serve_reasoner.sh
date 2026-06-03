#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv-cosmos3/bin/activate

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

vllm serve nvidia/Cosmos3-Nano \
  --hf-overrides '{"architectures": ["Cosmos3ReasonerForConditionalGeneration"]}' \
  --tensor-parallel-size "${COSMOS3_TENSOR_PARALLEL_SIZE:-1}" \
  --mm-encoder-tp-mode data \
  --async-scheduling \
  --allowed-local-media-path / \
  --media-io-kwargs '{"video": {"num_frames": -1}}' \
  --host "${COSMOS3_HOST:-0.0.0.0}" \
  --port "${COSMOS3_PORT:-8000}"
