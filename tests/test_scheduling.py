from datetime import date

from waterleaf.models import CareBenchmark, PlantContext, WeatherDay
from waterleaf.scheduling import build_watering_schedule


def test_container_plant_uses_shorter_interval():
    schedule = build_watering_schedule(
        start=date(2026, 6, 8),
        days=30,
        care=CareBenchmark(min_days=6, max_days=8),
        context=PlantContext(is_container=True, size_label="medium"),
        weather=[],
    )

    assert [item.date for item in schedule[:3]] == [
        date(2026, 6, 13),
        date(2026, 6, 18),
        date(2026, 6, 23),
    ]
    assert all(item.confidence == "baseline" for item in schedule[:3])


def test_meaningful_rain_defers_near_term_watering():
    schedule = build_watering_schedule(
        start=date(2026, 6, 8),
        days=16,
        care=CareBenchmark(min_days=4, max_days=4),
        context=PlantContext(is_container=False, size_label="large"),
        weather=[
            WeatherDay(
                date=date(2026, 6, 12),
                precipitation_mm=8.0,
                max_temperature_c=19.0,
                et0_mm=2.0,
            )
        ],
    )

    assert schedule[0].date == date(2026, 6, 14)
    assert schedule[0].reason == "Deferred after forecast rain"
    assert schedule[0].confidence == "forecast"


def test_high_heat_advances_near_term_watering_by_one_day():
    schedule = build_watering_schedule(
        start=date(2026, 6, 8),
        days=16,
        care=CareBenchmark(min_days=5, max_days=5),
        context=PlantContext(is_container=False, size_label="small"),
        weather=[
            WeatherDay(
                date=date(2026, 6, 13),
                precipitation_mm=0.0,
                max_temperature_c=32.0,
                et0_mm=5.8,
            )
        ],
    )

    assert schedule[0].date == date(2026, 6, 12)
    assert schedule[0].reason == "Advanced for hot, drying weather"


def test_dates_after_forecast_window_are_marked_seasonal():
    schedule = build_watering_schedule(
        start=date(2026, 6, 8),
        days=30,
        care=CareBenchmark(min_days=7, max_days=7),
        context=PlantContext(is_container=False, size_label="medium"),
        weather=[],
    )

    assert schedule[2].date == date(2026, 6, 29)
    assert schedule[2].confidence == "seasonal"
    assert schedule[2].reason == "Seasonal care baseline"


def test_missing_care_interval_requires_user_input():
    try:
        build_watering_schedule(
            start=date(2026, 6, 8),
            days=30,
            care=CareBenchmark(min_days=None, max_days=None),
            context=PlantContext(is_container=False, size_label="medium"),
            weather=[],
        )
    except ValueError as exc:
        assert str(exc) == "A watering interval is required"
    else:
        raise AssertionError("Expected a missing interval to be rejected")
