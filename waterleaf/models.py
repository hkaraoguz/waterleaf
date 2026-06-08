from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class CareBenchmark:
    min_days: int | None
    max_days: int | None

    @property
    def interval_days(self) -> int:
        if self.min_days is None or self.max_days is None:
            raise ValueError("A watering interval is required")
        if self.min_days < 1 or self.max_days < self.min_days:
            raise ValueError("Watering interval must be positive and ordered")
        return round((self.min_days + self.max_days) / 2)


@dataclass(frozen=True)
class PlantContext:
    is_container: bool
    size_label: str


@dataclass(frozen=True)
class WeatherDay:
    date: date
    precipitation_mm: float
    max_temperature_c: float
    et0_mm: float


@dataclass(frozen=True)
class WateringEvent:
    date: date
    reason: str
    confidence: str


@dataclass(frozen=True)
class PlantDraft:
    nickname: str
    common_name: str
    scientific_name: str
    taxon_key: str
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    preferred_time: time
    is_container: bool
    size_label: str
    image_id: str
    care_min_days: int | None
    care_max_days: int | None


@dataclass(frozen=True)
class SavedPlant:
    id: str
    owner: str
    public_slug: str
    nickname: str
    common_name: str
    scientific_name: str
    taxon_key: str
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    preferred_time: time
    is_container: bool
    size_label: str
    image_id: str
    care_min_days: int | None
    care_max_days: int | None


@dataclass(frozen=True)
class PublicPlant:
    public_slug: str
    nickname: str
    common_name: str
    scientific_name: str
    image_id: str
    is_container: bool
    size_label: str
    care_min_days: int | None
    care_max_days: int | None


class TaxonCandidate(BaseModel):
    taxon_key: str
    scientific_name: str
    common_name: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""


class VisualAnalysis(BaseModel):
    traits: list[str]
    proposed_names: list[str]
    is_container: bool
    size_label: str


class IdentificationResult(BaseModel):
    visual: VisualAnalysis
    candidates: list[TaxonCandidate]


class CareProfile(BaseModel):
    scientific_name: str
    common_name: str
    min_days: int | None = None
    max_days: int | None = None
    watering_label: str = ""
    sunlight: list[str] = []


class LocationMatch(BaseModel):
    display_name: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True)
class SchedulePlan:
    location: LocationMatch
    care: CareProfile
    events: list[WateringEvent]
    is_container: bool
    size_label: str
