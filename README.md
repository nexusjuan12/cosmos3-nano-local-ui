# Cosmos3-Nano Local UI

A small Gradio control panel for local NVIDIA Cosmos3-Nano generation.

It supports the local endpoints documented on the `nvidia/Cosmos3-Nano` model card:

- video generation with vLLM-Omni: `POST /v1/videos`, then polling and download through `/v1/videos/{id}/content`
- reasoner chat with vLLM: `POST /v1/chat/completions`

The model is served locally on `localhost:8000`; the UI runs locally on `localhost:7860`.

## Machine Check

This machine has an NVIDIA RTX PRO 6000 Blackwell GPU with about 98 GB VRAM, which should be suitable for the Nano model. Docker is not installed here, so this project uses NVIDIA's native `uv` setup path instead of the `vllm/vllm-omni:cosmos3` container.

## Install

Install UI and backend dependencies:

```bash
git clone https://github.com/nexusjuan12/cosmos3-nano-local-ui.git
cd cosmos3-nano-local-ui
./install.sh
```

For a lighter install that only prepares the Gradio UI:

```bash
./install.sh --ui-only
```

## Install The Local Backend

Run once:

```bash
./install_backend.sh
```

The script follows the model card's release-tested local setup:

```bash
uv venv --python 3.13 --seed --managed-python .venv-cosmos3
uv pip install --torch-backend=cu130 \
  "vllm==0.22.0" \
  "vllm-cosmos3 @ git+https://github.com/NVIDIA/cosmos-framework.git#subdirectory=packages/vllm-cosmos3" \
  "vllm-omni @ git+https://github.com/vllm-project/vllm-omni.git" \
  audioop-lts \
  cosmos-guardrail \
  opencv-python-headless \
  openai
```

If Hugging Face requires authentication for the model or license, run:

```bash
source .venv-cosmos3/bin/activate
hf auth login
```

For video generation, your Hugging Face account must have access to both:

- `nvidia/Cosmos3-Nano`
- `nvidia/Cosmos-1.0-Guardrail`

The guardrail repo is required by NVIDIA's Cosmos3 generation path; the server will not start without it.

## Start Local Generation

For video generation, run this in one terminal:

```bash
./serve_generator.sh
```

This starts a local server at `http://127.0.0.1:8000` with `POST /v1/videos`.

For reasoner chat, stop the generator server and run:

```bash
./serve_reasoner.sh
```

Cosmos3's documented generator and reasoner examples use different vLLM serving modes, so the scripts keep those modes separate.

## Start The UI

The UI dependencies are already installed in the system Python. Start it with:

```bash
./start_ui.sh
```

Open:

```text
http://127.0.0.1:7860
```

## Runtime Settings

- `COSMOS3_VIDEO_ENDPOINT`, default `http://127.0.0.1:8000/v1/videos`
- `COSMOS3_CHAT_ENDPOINT`, default `http://127.0.0.1:8000/v1/chat/completions`
- `COSMOS3_MODEL`, default `nvidia/Cosmos3-Nano`
- `COSMOS3_OUTPUT_DIR`, default `outputs/` inside the repo
- `GRADIO_SERVER_NAME`, default `0.0.0.0`
- `GRADIO_SERVER_PORT`, default `7860`
- `CUDA_VISIBLE_DEVICES`, default `0`
- `COSMOS3_PORT`, default `8000`

Generated videos are saved under `outputs/` by default. Outputs, virtual environments, model weights, caches, and local secrets are ignored by git.
