from __future__ import annotations

import json
from pathlib import Path

import httpx

from waterleaf.models import CareProfile

DEMO_CARE = {
    "Lavandula angustifolia": CareProfile(
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
        min_days=7,
        max_days=10,
        watering_label="Minimum",
        sunlight=["full sun"],
    ),
    "Salvia officinalis": CareProfile(
        scientific_name="Salvia officinalis",
        common_name="Common sage",
        min_days=7,
        max_days=10,
        watering_label="Minimum",
        sunlight=["full sun"],
    ),
}


class PerenualClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        cache_path: str | Path,
        http_client: httpx.Client | None = None,
        base_url: str = "https://perenual.com/api/v2",
    ):
        self.api_key = api_key
        self.cache_path = Path(cache_path)
        self.http_client = http_client or httpx.Client(timeout=20.0)
        self.base_url = base_url.rstrip("/")
        self._cache = self._load_cache()

    def get_care(self, scientific_name: str) -> CareProfile:
        if scientific_name in self._cache:
            return CareProfile.model_validate(self._cache[scientific_name])
        if not self.api_key:
            return self._remember_fallback(scientific_name)

        try:
            search = self.http_client.get(
                f"{self.base_url}/species-list",
                params={"key": self.api_key, "q": scientific_name},
            )
            search.raise_for_status()
            entries = search.json().get("data", [])
            if not entries:
                return self._remember_fallback(scientific_name)

            details = self.http_client.get(
                f"{self.base_url}/species/details/{entries[0]['id']}",
                params={"key": self.api_key},
            )
            details.raise_for_status()
            payload = details.json()
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return self._remember_fallback(scientific_name)

        min_days, max_days = _parse_benchmark(payload.get("watering_general_benchmark"))
        scientific = payload.get("scientific_name") or [scientific_name]
        profile = CareProfile(
            scientific_name=scientific[0] if isinstance(scientific, list) else scientific,
            common_name=payload.get("common_name") or scientific_name,
            min_days=min_days,
            max_days=max_days,
            watering_label=payload.get("watering") or "",
            sunlight=payload.get("sunlight") or [],
        )
        self._remember(scientific_name, profile)
        return profile

    def _remember_fallback(self, scientific_name: str) -> CareProfile:
        profile = DEMO_CARE.get(scientific_name) or CareProfile(
            scientific_name=scientific_name,
            common_name=scientific_name,
        )
        self._remember(scientific_name, profile)
        return profile

    def _load_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _remember(self, key: str, profile: CareProfile) -> None:
        self._cache[key] = profile.model_dump()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache, indent=2, sort_keys=True))


def _parse_benchmark(payload: dict | None) -> tuple[int | None, int | None]:
    if not payload or payload.get("unit") != "days":
        return None, None
    value = payload.get("value")
    if isinstance(value, int):
        return value, value
    if isinstance(value, str):
        parts = value.replace(" ", "").split("-")
        try:
            if len(parts) == 1:
                parsed = int(parts[0])
                return parsed, parsed
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None
    return None, None
