from __future__ import annotations

import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import gradio as gr
import requests


DEFAULT_VIDEO_ENDPOINT = os.getenv("COSMOS3_VIDEO_ENDPOINT", "http://127.0.0.1:8000/v1/videos")
DEFAULT_CHAT_ENDPOINT = os.getenv("COSMOS3_CHAT_ENDPOINT", "http://127.0.0.1:8000/v1/chat/completions")
DEFAULT_MODEL = os.getenv("COSMOS3_MODEL", "nvidia/Cosmos3-Nano")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR = Path(os.getenv("COSMOS3_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _coerce_prompt(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise gr.Error("Prompt is required.")

    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise gr.Error(f"Prompt looks like JSON but is invalid: {exc}") from exc
        return json.dumps(parsed)

    return text


def _coerce_negative_prompt(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise gr.Error(f"Negative prompt looks like JSON but is invalid: {exc}") from exc
        return json.dumps(parsed)

    return text


def _extra_params(guardrails: bool, resolution_template: bool, duration_template: bool) -> str:
    return json.dumps(
        {
            "guardrails": guardrails,
            "use_resolution_template": resolution_template,
            "use_duration_template": duration_template,
        }
    )


def check_endpoint(base_url: str) -> str:
    endpoint = (base_url or "").strip().rstrip("/")
    if not endpoint:
        raise gr.Error("Base URL is required.")

    try:
        response = requests.get(f"{endpoint}/v1/models", timeout=20)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.RequestException as exc:
        raise gr.Error(f"Local Cosmos3 server is not reachable at {endpoint}: {exc}") from exc
    except ValueError:
        return response.text


def _raise_response_error(prefix: str, response: requests.Response) -> None:
    detail = response.text.strip()
    if len(detail) > 1200:
        detail = detail[:1200] + "..."
    raise gr.Error(f"{prefix}: HTTP {response.status_code} {response.reason}. {detail}")


def _async_video_endpoint(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/sync"):
        return endpoint[: -len("/sync")]
    return endpoint


def generate_video(
    prompt: str,
    negative_prompt: str,
    input_reference: str | None,
    endpoint_url: str,
    size: str,
    num_frames: int,
    fps: int,
    num_inference_steps: int,
    guidance_scale: float,
    flow_shift: float,
    max_sequence_length: int,
    seed: int,
    generate_sound: bool,
    sound_duration: float,
    guardrails: bool,
    use_resolution_template: bool,
    use_duration_template: bool,
    timeout_seconds: int,
) -> tuple[str, str, str]:
    endpoint = (endpoint_url or "").strip()
    if not endpoint:
        raise gr.Error("Video endpoint URL is required.")
    endpoint = _async_video_endpoint(endpoint)

    data = {
        "prompt": _coerce_prompt(prompt),
        "negative_prompt": _coerce_negative_prompt(negative_prompt),
        "size": size,
        "num_frames": str(num_frames),
        "fps": str(fps),
        "num_inference_steps": str(num_inference_steps),
        "guidance_scale": str(guidance_scale),
        "max_sequence_length": str(max_sequence_length),
        "flow_shift": str(flow_shift),
        "extra_params": _extra_params(guardrails, use_resolution_template, use_duration_template),
        "seed": str(seed),
    }

    if generate_sound:
        data["generate_sound"] = "true"
        data["sound_duration"] = str(sound_duration)

    files: dict[str, Any] | None = None
    file_handle = None
    try:
        if input_reference:
            reference_path = Path(input_reference)
            mime_type = mimetypes.guess_type(reference_path.name)[0] or "application/octet-stream"
            file_handle = reference_path.open("rb")
            files = {
                "input_reference": (reference_path.name, file_handle, mime_type),
            }

        started = time.time()
        create_response = requests.post(
            endpoint,
            data=data,
            files=files,
            timeout=timeout_seconds,
        )
        if not create_response.ok:
            _raise_response_error("Video job creation failed", create_response)
        job = create_response.json()
        video_id = job.get("id")
        if not video_id:
            raise gr.Error(f"Video job creation did not return an id: {json.dumps(job, indent=2)}")

        status_url = f"{endpoint}/{video_id}"
        content_url = f"{status_url}/content"
        deadline = started + timeout_seconds
        poll_interval = 5.0
        last_job = job

        while time.time() < deadline:
            status_response = requests.get(status_url, timeout=30)
            if not status_response.ok:
                _raise_response_error("Video job status request failed", status_response)

            last_job = status_response.json()
            status = str(last_job.get("status", "")).lower()
            if status == "completed":
                break
            if status == "failed":
                raise gr.Error(f"Video generation failed: {json.dumps(last_job, indent=2)}")
            time.sleep(poll_interval)
        else:
            raise gr.Error(f"Timed out waiting for video job {video_id}. Last status: {json.dumps(last_job, indent=2)}")

        response = requests.get(content_url, headers={"Accept": "video/mp4"}, timeout=timeout_seconds)
        if not response.ok:
            _raise_response_error("Video download failed", response)
    except requests.RequestException as exc:
        raise gr.Error(f"Video request failed: {exc}") from exc
    except ValueError as exc:
        raise gr.Error(f"Video endpoint returned invalid JSON: {exc}") from exc
    finally:
        if file_handle:
            file_handle.close()

    output_path = OUTPUT_DIR / f"cosmos3_video_{time.time_ns()}.mp4"
    output_path.write_bytes(response.content)

    metadata = {
        "saved_to": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "response_content_type": response.headers.get("content-type"),
        "elapsed_seconds": round(time.time() - started, 2),
        "endpoint": endpoint,
        "job": last_job,
        "request": data,
        "used_input_reference": bool(input_reference),
    }
    return str(output_path), str(output_path), json.dumps(metadata, indent=2)


def reason(
    message: str,
    image: str | None,
    endpoint_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> str:
    endpoint = (endpoint_url or "").strip()
    if not endpoint:
        raise gr.Error("Chat endpoint URL is required.")
    if not (message or "").strip():
        raise gr.Error("Message is required.")

    content: list[dict[str, Any]] = [{"type": "text", "text": message.strip()}]
    if image:
        import base64

        image_path = Path(image)
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        raise gr.Error(f"Reasoning request failed: {exc}") from exc
    except ValueError as exc:
        raise gr.Error(f"Chat endpoint did not return JSON: {exc}") from exc

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(body, indent=2)


with gr.Blocks(title="Cosmos3-Nano UI", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Cosmos3-Nano Local UI
        Run Cosmos3-Nano locally, then use this UI against `localhost`. Text prompts can be plain text or NVIDIA's JSON-upsampled prompt format.
        """
    )

    with gr.Row():
        status_base_url = gr.Textbox(label="Local server base URL", value="http://127.0.0.1:8000")
        status_button = gr.Button("Check Local Server")
    status_output = gr.Code(label="Local server models", language="json")
    status_button.click(check_endpoint, inputs=status_base_url, outputs=status_output)

    with gr.Tabs():
        with gr.Tab("Video"):
            with gr.Row():
                with gr.Column(scale=5):
                    video_prompt = gr.Textbox(
                        label="Prompt",
                        lines=7,
                        placeholder="A small warehouse robot moves a blue box across a clean floor.",
                    )
                    video_negative = gr.Textbox(label="Negative prompt", lines=3)
                    video_reference = gr.File(
                        label="Input reference image/video (optional)",
                        type="filepath",
                        file_types=["image", "video"],
                    )
                with gr.Column(scale=3):
                    video_endpoint = gr.Textbox(label="Video endpoint", value=DEFAULT_VIDEO_ENDPOINT)
                    size = gr.Dropdown(
                        label="Size",
                        choices=["1280x720", "720x1280", "960x544", "544x960", "704x704"],
                        value="1280x720",
                        allow_custom_value=True,
                    )
                    with gr.Row():
                        num_frames = gr.Number(label="Frames", value=189, precision=0)
                        fps = gr.Number(label="FPS", value=24, precision=0)
                    with gr.Row():
                        steps = gr.Number(label="Steps", value=35, precision=0)
                        seed = gr.Number(label="Seed", value=123, precision=0)
                    guidance = gr.Slider(label="Guidance scale", minimum=0, maximum=20, value=6.0, step=0.1)
                    flow_shift = gr.Slider(label="Flow shift", minimum=0, maximum=20, value=10.0, step=0.1)
                    max_sequence = gr.Number(label="Max sequence length", value=4096, precision=0)
                    with gr.Row():
                        sound = gr.Checkbox(label="Generate sound", value=False)
                        guardrails = gr.Checkbox(label="Guardrails", value=True)
                    with gr.Row():
                        resolution_template = gr.Checkbox(label="Resolution template", value=False)
                        duration_template = gr.Checkbox(label="Duration template", value=False)
                    sound_duration = gr.Number(label="Sound duration seconds", value=7.875)
                    video_timeout = gr.Number(label="Timeout seconds", value=1800, precision=0)
                    generate_video_button = gr.Button("Generate Video", variant="primary")

            with gr.Row():
                video_output = gr.Video(label="Output video", format="mp4", include_audio=True)
                video_download = gr.File(label="Download video")
                video_metadata = gr.Code(label="Request metadata", language="json")

            generate_video_button.click(
                generate_video,
                inputs=[
                    video_prompt,
                    video_negative,
                    video_reference,
                    video_endpoint,
                    size,
                    num_frames,
                    fps,
                    steps,
                    guidance,
                    flow_shift,
                    max_sequence,
                    seed,
                    sound,
                    sound_duration,
                    guardrails,
                    resolution_template,
                    duration_template,
                    video_timeout,
                ],
                outputs=[video_output, video_download, video_metadata],
            )

        with gr.Tab("Reasoner"):
            reason_message = gr.Textbox(label="Message", lines=6)
            reason_image = gr.File(label="Image input (optional)", type="filepath", file_types=["image"])
            with gr.Row():
                chat_endpoint = gr.Textbox(label="Chat endpoint", value=DEFAULT_CHAT_ENDPOINT)
                chat_model = gr.Textbox(label="Model", value=DEFAULT_MODEL)
            with gr.Row():
                temperature = gr.Slider(label="Temperature", minimum=0, maximum=2, value=0.2, step=0.05)
                max_tokens = gr.Number(label="Max tokens", value=1024, precision=0)
                chat_timeout = gr.Number(label="Timeout seconds", value=300, precision=0)
            reason_button = gr.Button("Run Reasoner", variant="primary")
            reason_output = gr.Markdown(label="Output")
            reason_button.click(
                reason,
                inputs=[reason_message, reason_image, chat_endpoint, chat_model, temperature, max_tokens, chat_timeout],
                outputs=reason_output,
            )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
