from __future__ import annotations

import hashlib
from datetime import date, time
from pathlib import Path
from typing import Protocol

from waterleaf.calendar import CalendarPlant, build_garden_ics
from waterleaf.images import normalize_plant_image
from waterleaf.models import (
    CareBenchmark,
    CareProfile,
    LocationMatch,
    PlantContext,
    PlantDraft,
    SavedPlant,
    SchedulePlan,
    TaxonCandidate,
    WateringEvent,
    WeatherDay,
)
from waterleaf.scheduling import build_watering_schedule
from waterleaf.storage import GardenStore


class CareService(Protocol):
    def get_care(self, scientific_name: str) -> CareProfile: ...


class WeatherService(Protocol):
    def geocode(self, query: str) -> LocationMatch: ...

    def forecast(self, latitude: float, longitude: float) -> list[WeatherDay]: ...


class WaterleafApplication:
    def __init__(
        self,
        *,
        store: GardenStore,
        media_directory: str | Path,
        export_directory: str | Path,
        public_base_url: str,
        care: CareService,
        weather: WeatherService,
        identification: object | None = None,
        taxonomy: object | None = None,
    ):
        self.store = store
        self.media_directory = Path(media_directory)
        self.export_directory = Path(export_directory)
        self.public_base_url = public_base_url.rstrip("/")
        self.care = care
        self.weather = weather
        self.identification = identification
        self.taxonomy = taxonomy
        self.media_directory.mkdir(parents=True, exist_ok=True)
        self.export_directory.mkdir(parents=True, exist_ok=True)

    def preview_schedule(
        self,
        *,
        candidate: TaxonCandidate,
        location_query: str,
        is_container: bool,
        size_label: str,
        start: date | None = None,
        manual_interval_days: int | None = None,
    ) -> SchedulePlan:
        location = self.weather.geocode(location_query)
        care = self.care.get_care(candidate.scientific_name)
        if manual_interval_days:
            min_days = max(1, int(manual_interval_days))
            max_days = min_days
        else:
            min_days = care.min_days
            max_days = care.max_days
        weather = self.weather.forecast(location.latitude, location.longitude)
        events = build_watering_schedule(
            start=start or date.today(),
            days=30,
            care=CareBenchmark(min_days=min_days, max_days=max_days),
            context=PlantContext(is_container=is_container, size_label=size_label),
            weather=weather,
        )
        return SchedulePlan(
            location=location,
            care=care,
            events=events,
            is_container=is_container,
            size_label=size_label,
        )

    def save_plant(
        self,
        *,
        owner: str,
        nickname: str,
        candidate: TaxonCandidate,
        source_image: str | Path,
        preferred_time: time,
        plan: SchedulePlan,
        edited_events: list[WateringEvent] | None = None,
    ) -> SavedPlant:
        image = normalize_plant_image(source_image, self.media_directory)
        plant = self.store.save_plant(
            owner,
            PlantDraft(
                nickname=nickname,
                common_name=candidate.common_name,
                scientific_name=candidate.scientific_name,
                taxon_key=candidate.taxon_key,
                location_name=plan.location.display_name,
                latitude=plan.location.latitude,
                longitude=plan.location.longitude,
                timezone=plan.location.timezone,
                preferred_time=preferred_time,
                is_container=plan.is_container,
                size_label=plan.size_label,
                image_id=image.id,
                care_min_days=plan.care.min_days,
                care_max_days=plan.care.max_days,
            ),
        )
        events = edited_events if edited_events is not None else plan.events
        self.store.replace_schedule(
            owner,
            plant.id,
            [
                {
                    "date": item.date.isoformat(),
                    "reason": item.reason,
                    "confidence": item.confidence,
                }
                for item in events
            ],
        )
        return plant

    def delete_plant(self, owner: str, plant_id: str) -> bool:
        plant = self.store.get_plant(owner, plant_id)
        if plant is None or not self.store.delete_plant(owner, plant_id):
            return False
        if self.store.image_reference_count(plant.image_id) == 0:
            (self.media_directory / f"{plant.image_id}.jpg").unlink(missing_ok=True)
        return True

    def export_garden(
        self,
        owner: str,
        *,
        generated_at: str | None = None,
    ) -> Path:
        calendar_plants: list[CalendarPlant] = []
        for plant in self.store.list_plants(owner):
            events = [
                WateringEvent(
                    date=date.fromisoformat(item["date"]),
                    reason=item["reason"],
                    confidence=item["confidence"],
                )
                for item in self.store.get_schedule(owner, plant.id)
            ]
            calendar_plants.append(
                CalendarPlant(
                    id=plant.id,
                    nickname=plant.nickname,
                    common_name=plant.common_name,
                    scientific_name=plant.scientific_name,
                    timezone=plant.timezone,
                    preferred_time=plant.preferred_time,
                    profile_url=f"{self.public_base_url}/plants/{plant.public_slug}",
                    image_url=f"{self.public_base_url}/media/{plant.image_id}.jpg",
                    events=events,
                )
            )
        if not calendar_plants:
            raise ValueError("Add at least one plant before exporting")
        owner_token = hashlib.sha256(owner.encode()).hexdigest()[:12]
        destination = self.export_directory / f"waterleaf-{owner_token}.ics"
        destination.write_text(
            build_garden_ics(calendar_plants, generated_at=generated_at),
            newline="",
        )
        return destination
