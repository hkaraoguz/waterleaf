from __future__ import annotations

from collections.abc import Sequence


def score_predictions(rows: Sequence[dict]) -> dict[str, float | int]:
    count = len(rows)
    if count == 0:
        return {
            "count": 0,
            "species_top_1": 0.0,
            "species_top_3": 0.0,
            "genus_top_1": 0.0,
        }

    species_top_1 = 0
    species_top_3 = 0
    genus_top_1 = 0
    for row in rows:
        expected = _normalize(row["expected"])
        predictions = [_normalize(value) for value in row.get("predictions", [])]
        if predictions and predictions[0] == expected:
            species_top_1 += 1
        if expected in predictions[:3]:
            species_top_3 += 1
        if predictions and _genus(predictions[0]) == _genus(expected):
            genus_top_1 += 1

    return {
        "count": count,
        "species_top_1": species_top_1 / count,
        "species_top_3": species_top_3 / count,
        "genus_top_1": genus_top_1 / count,
    }


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _genus(scientific_name: str) -> str:
    return scientific_name.split(" ", maxsplit=1)[0]

