from __future__ import annotations

from collections import Counter
from typing import Any

import httpx

from waterleaf.models import TaxonCandidate

PLANTAE_KEY = 6


class GbifClient:
    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        base_url: str = "https://api.gbif.org/v1",
    ):
        self.http_client = http_client or httpx.Client(timeout=15.0)
        self.base_url = base_url.rstrip("/")

    def suggest(self, query: str, limit: int = 10) -> list[TaxonCandidate]:
        query = query.strip()
        if len(query) < 2:
            return []
        response = self.http_client.get(
            f"{self.base_url}/species/search",
            params={
                "q": query,
                "rank": "SPECIES",
                "highertaxon_key": PLANTAE_KEY,
                "language": "en",
                "limit": min(max(limit * 3, 20), 100),
            },
            headers={"User-Agent": "Waterleaf/0.1 karaoguzh@gmail.com"},
        )
        response.raise_for_status()
        matches: list[tuple[int, TaxonCandidate]] = []
        seen: set[str] = set()
        for item in response.json().get("results", []):
            if item.get("kingdom") != "Plantae" or item.get("rank") != "SPECIES":
                continue
            key = str(item.get("key", ""))
            if not key or key in seen:
                continue
            scientific_name = item.get("canonicalName") or item.get("scientificName")
            if not scientific_name:
                continue
            seen.add(key)
            common_name = _common_name(item, query) or scientific_name
            candidate = TaxonCandidate(
                taxon_key=key,
                scientific_name=scientific_name,
                common_name=common_name,
            )
            matches.append(
                (
                    _match_score(
                        query=query,
                        scientific_name=scientific_name,
                        common_name=common_name,
                        status=str(item.get("taxonomicStatus", "")),
                    ),
                    candidate,
                )
            )
        matches.sort(
            key=lambda match: (
                -match[0],
                match[1].common_name.casefold(),
                match[1].scientific_name.casefold(),
            )
        )
        candidates: list[TaxonCandidate] = []
        seen_scientific_names: set[str] = set()
        for _, candidate in matches:
            scientific_name = candidate.scientific_name.casefold()
            if scientific_name in seen_scientific_names:
                continue
            seen_scientific_names.add(scientific_name)
            candidates.append(candidate)
            if len(candidates) == limit:
                break
        return candidates


def _common_name(item: dict[str, Any], query: str) -> str | None:
    names = [
        str(record.get("vernacularName", "")).strip()
        for record in item.get("vernacularNames", [])
        if str(record.get("language", "")).casefold() in {"en", "eng", "english"}
        and str(record.get("vernacularName", "")).strip()
    ]
    direct = str(item.get("vernacularName", "")).strip()
    if direct:
        names.append(direct)
    if not names:
        return None

    displays: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for name in names:
        normalized = name.casefold()
        displays.setdefault(normalized, name)
        counts[normalized] += 1
    query_normalized = query.casefold()
    best = min(
        counts,
        key=lambda name: (
            name != query_normalized,
            query_normalized not in name,
            -counts[name],
            len(name),
            name,
        ),
    )
    return displays[best]


def _match_score(
    *,
    query: str,
    scientific_name: str,
    common_name: str,
    status: str,
) -> int:
    needle = query.casefold()
    scientific = scientific_name.casefold()
    common = common_name.casefold()
    score = 0
    if common != scientific:
        if common == needle:
            score += 1000
        elif needle in common:
            score += 300
    if scientific == needle:
        score += 900
    elif scientific.startswith(needle):
        score += 250
    if status.casefold() == "accepted":
        score += 100
    return score
