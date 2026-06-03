#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Python:"
python3 --version

echo
echo "GPU:"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
  echo "nvidia-smi not found"
fi

echo
echo "UI dependencies:"
python3 -m pip show gradio requests imageio imageio-ffmpeg >/dev/null && echo "ok" || echo "missing UI deps"

echo
echo "Backend environment:"
if [[ -d .venv-cosmos3 ]]; then
  source .venv-cosmos3/bin/activate
  python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available())
PY
  python -m pip show vllm vllm-omni vllm-cosmos3 cosmos-guardrail >/dev/null && echo "backend packages ok" || echo "missing backend packages"
  hf auth whoami || true
else
  echo ".venv-cosmos3 not installed"
fi
