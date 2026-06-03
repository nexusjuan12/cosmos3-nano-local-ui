#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m pip install -U uv

uv venv --python 3.13 --seed --managed-python .venv-cosmos3
source .venv-cosmos3/bin/activate

uv pip install --torch-backend=cu130 \
  "vllm==0.22.0" \
  "vllm-cosmos3 @ git+https://github.com/NVIDIA/cosmos-framework.git#subdirectory=packages/vllm-cosmos3" \
  "vllm-omni @ git+https://github.com/vllm-project/vllm-omni.git" \
  audioop-lts \
  cosmos-guardrail \
  opencv-python-headless \
  openai \
  requests \
  "huggingface_hub[cli]"

echo
echo "Cosmos3 backend environment installed in $(pwd)/.venv-cosmos3"
echo "Run ./serve_generator.sh for local video generation."
echo "Run ./serve_reasoner.sh for local reasoning."
