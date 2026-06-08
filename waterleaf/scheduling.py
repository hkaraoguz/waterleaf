from __future__ import annotations

from datetime import date, timedelta

from waterleaf.models import CareBenchmark, PlantContext, WateringEvent, WeatherDay

FORECAST_WINDOW_DAYS = 16
CONTAINER_INTERVAL_FACTOR = 0.75
RAIN_THRESHOLD_MM = 5.0
HOT_TEMPERATURE_C = 30.0
HIGH_ET0_MM = 5.0


def build_watering_schedule(
    *,
    start: date,
    days: int,
    care: CareBenchmark,
    context: PlantContext,
    weather: list[WeatherDay],
) -> list[WateringEvent]:
    if days < 1:
        return []

    interval = care.interval_days
    if context.is_container:
        interval = max(1, round(interval * CONTAINER_INTERVAL_FACTOR))

    weather_by_date = {item.date: item for item in weather}
    horizon = start + timedelta(days=days)
    candidate = start + timedelta(days=interval)
    events: list[WateringEvent] = []

    while candidate <= horizon:
        event_date, reason, confidence = _adjust_candidate(
            start=start,
            candidate=candidate,
            weather=weather_by_date,
        )
        if event_date > horizon:
            break
        if not events or event_date > events[-1].date:
            events.append(
                WateringEvent(
                    date=event_date,
                    reason=reason,
                    confidence=confidence,
                )
            )
        candidate = event_date + timedelta(days=interval)

    return events


def _adjust_candidate(
    *,
    start: date,
    candidate: date,
    weather: dict[date, WeatherDay],
) -> tuple[date, str, str]:
    day_number = (candidate - start).days
    if day_number > FORECAST_WINDOW_DAYS:
        return candidate, "Seasonal care baseline", "seasonal"

    nearby = [
        weather.get(candidate - timedelta(days=1)),
        weather.get(candidate),
    ]
    if any(item and item.precipitation_mm >= RAIN_THRESHOLD_MM for item in nearby):
        return candidate + timedelta(days=2), "Deferred after forecast rain", "forecast"

    current = weather.get(candidate)
    if current and (
        current.max_temperature_c >= HOT_TEMPERATURE_C or current.et0_mm >= HIGH_ET0_MM
    ):
        return candidate - timedelta(days=1), "Advanced for hot, drying weather", "forecast"

    return candidate, "Species care baseline", "baseline"

