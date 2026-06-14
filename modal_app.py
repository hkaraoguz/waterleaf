"""Modal deployment for Gemma 4 vision inference through llama.cpp."""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request

import modal

APP_NAME = "waterleaf-gemma4"
PORT = 8000
MODEL_REPO = "ggml-org/gemma-4-26B-A4B-it-GGUF"
PRIMARY_QUANT = "Q4_K_M"
FALLBACK_QUANT = PRIMARY_QUANT
LLAMA_IMAGE = "ghcr.io/ggml-org/llama.cpp:server-cuda13-b9445"
PROXY_AUTH_REQUIRED = os.getenv("MODAL_PROXY_AUTH", "1") != "0"

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name("waterleaf-model-cache", create_if_missing=True)
minimum_containers = int(os.getenv("MODAL_MIN_CONTAINERS", "0"))
image = (
    modal.Image.from_registry(LLAMA_IMAGE, add_python="3.12")
    .entrypoint([])
    .env(
        {
            "HF_HOME": "/models/huggingface",
            "LLAMA_CACHE": "/models/llama.cpp",
            "HF_XET_HIGH_PERFORMANCE": "1",
        }
    )
)


@app.function(
    image=image,
    gpu="L4",
    memory=32768,
    volumes={"/models": model_cache},
    startup_timeout=900,
    timeout=900,
    scaledown_window=600,
    min_containers=minimum_containers,
    max_containers=1,
)
@modal.concurrent(max_inputs=1)
@modal.web_server(
    PORT,
    startup_timeout=900,
    requires_proxy_auth=PROXY_AUTH_REQUIRED,
)
def serve() -> None:
    requested = os.getenv("WATERLEAF_MODEL_QUANT", PRIMARY_QUANT)
    attempts = list(dict.fromkeys([requested, FALLBACK_QUANT]))
    errors: list[str] = []
    for quant in attempts:
        process = subprocess.Popen(_command(quant))
        if _wait_until_ready(process, timeout_seconds=780):
            print(f"Waterleaf llama.cpp ready with {quant}", flush=True)
            return
        errors.append(f"{quant}: exit={process.poll()}")
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=20)
    raise RuntimeError("llama.cpp failed to start; " + ", ".join(errors))


def _command(quant: str) -> list[str]:
    return [
        "/app/llama-server",
        "-hf",
        f"{MODEL_REPO}:{quant}",
        "--alias",
        "waterleaf-gemma-4",
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
        "--ctx-size",
        "8192",
        "--n-gpu-layers",
        "99",
        "--flash-attn",
        "on",
        "--cache-type-k",
        "q8_0",
        "--cache-type-v",
        "q8_0",
        "--parallel",
        "1",
        "--jinja",
        "--reasoning",
        "auto",
        "--reasoning-format",
        "deepseek",
        "--reasoning-budget",
        "256",
    ]


def _wait_until_ready(process: subprocess.Popen, *, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/health",
                timeout=2,
            ) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(2)
    return False
