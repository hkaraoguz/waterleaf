from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from waterleaf.services.llama_cpp import LlamaCppClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live llama.cpp vision smoke test.")
    parser.add_argument("images", type=Path, nargs="+")
    args = parser.parse_args()
    endpoint = os.environ["MODAL_ENDPOINT"]
    client = LlamaCppClient(
        endpoint=endpoint,
        modal_key=os.getenv("MODAL_KEY"),
        modal_secret=os.getenv("MODAL_SECRET"),
    )
    started = time.perf_counter()
    result = client.analyze_images(args.images)
    elapsed = time.perf_counter() - started
    print(result.model_dump_json(indent=2))
    print(f"latency_seconds={elapsed:.3f}")


if __name__ == "__main__":
    main()

