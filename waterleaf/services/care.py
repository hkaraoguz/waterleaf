from __future__ import annotations

from waterleaf.models import CareProfile

LOCAL_CARE_PROFILES = {
    "lavandula angustifolia": CareProfile(
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
        min_days=7,
        max_days=10,
        watering_label="Minimum",
        sunlight=["full sun"],
    ),
    "salvia officinalis": CareProfile(
        scientific_name="Salvia officinalis",
        common_name="Common sage",
        min_days=7,
        max_days=10,
        watering_label="Minimum",
        sunlight=["full sun"],
    ),
    "solanum lycopersicum": CareProfile(
        scientific_name="Solanum lycopersicum",
        common_name="Tomato",
        min_days=2,
        max_days=4,
        watering_label="Frequent",
        sunlight=["full sun"],
    ),
}

LOCAL_GENUS_PROFILES = {
    "lavandula": CareProfile(
        scientific_name="Lavandula",
        common_name="Lavender",
        min_days=7,
        max_days=10,
        watering_label="Minimum",
        sunlight=["full sun"],
    ),
}


class LocalCareCatalog:
    def get_care(self, scientific_name: str) -> CareProfile:
        normalized = _normalize_scientific_name(scientific_name)
        profile = LOCAL_CARE_PROFILES.get(normalized)
        if profile is None:
            profile = LOCAL_GENUS_PROFILES.get(normalized.split(" ", 1)[0])
        if profile is None:
            return CareProfile(
                scientific_name=scientific_name,
                common_name=scientific_name,
            )
        return profile.model_copy(update={"scientific_name": scientific_name})


def _normalize_scientific_name(scientific_name: str) -> str:
    tokens = scientific_name.replace("×", "x").casefold().split()
    if len(tokens) >= 3 and tokens[1] == "x":
        return " ".join(tokens[:3])
    return " ".join(tokens[:2])
