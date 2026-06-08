from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx

from waterleaf.models import TaxonCandidate, VisualAnalysis

VISUAL_SCHEMA = {
    "type": "object",
    "properties": {
        "traits": {"type": "array", "items": {"type": "string"}},
        "proposed_names": {"type": "array", "items": {"type": "string"}},
        "is_container": {"type": "boolean"},
        "size_label": {"type": "string", "enum": ["small", "medium", "large"]},
    },
    "required": ["traits", "proposed_names", "is_container", "size_label"],
    "additionalProperties": False,
}

RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranking": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "taxon_key": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                },
                "required": ["taxon_key", "confidence", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ranking"],
    "additionalProperties": False,
}


class LlamaCppClient:
    def __init__(
        self,
        *,
        endpoint: str,
        modal_key: str | None = None,
        modal_secret: str | None = None,
        http_client: httpx.Client | None = None,
        max_startup_wait_seconds: float = 120.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.http_client = http_client or httpx.Client(timeout=180.0)
        self.max_startup_wait_seconds = max_startup_wait_seconds
        self.headers = {"Authorization": "Bearer waterleaf"}
        if modal_key and modal_secret:
            self.headers.update({"Modal-Key": modal_key, "Modal-Secret": modal_secret})

    def analyze_images(self, image_paths: list[Path]) -> VisualAnalysis:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Identify visible botanical traits and propose up to five likely species. "
                    "Infer only visible context: container versus in-ground and rough size."
                ),
            }
        ]
        content.extend(_image_part(path) for path in image_paths)
        payload = self._completion_payload(
            content,
            schema_name="visual_analysis",
            schema=VISUAL_SCHEMA,
        )
        result = self._post(payload)
        return VisualAnalysis.model_validate(result)

    def rerank(
        self,
        image_paths: list[Path],
        visual: VisualAnalysis,
        candidates: list[TaxonCandidate],
    ) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Rank only these database candidates against the images and observed traits. "
                    "Do not add species. Candidates: "
                    + json.dumps([item.model_dump() for item in candidates])
                    + " Traits: "
                    + json.dumps(visual.traits)
                ),
            }
        ]
        content.extend(_image_part(path) for path in image_paths)
        result = self._post(
            self._completion_payload(
                content,
                schema_name="candidate_ranking",
                schema=RERANK_SCHEMA,
                enable_thinking=True,
            )
        )
        return result["ranking"]

    def _completion_payload(
        self,
        content: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
        enable_thinking: bool = False,
    ) -> dict[str, Any]:
        return {
            "model": "waterleaf-gemma-4",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cautious plant identification assistant. Return only JSON "
                        "matching the requested schema. Never claim certainty from an image."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0.1,
            "max_tokens": 700,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + self.max_startup_wait_seconds
        while True:
            response = self.http_client.post(
                f"{self.endpoint}/v1/chat/completions",
                headers=self.headers,
                json=payload,
            )
            if response.status_code != 503:
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]["content"]
                return json.loads(message)
            if time.monotonic() >= deadline:
                raise TimeoutError("Modal model did not become ready")
            time.sleep(1)


def _image_part(path: Path) -> dict[str, Any]:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{encoded}"},
    }
