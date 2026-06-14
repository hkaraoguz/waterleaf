from datetime import date, time

from waterleaf.calendar import CalendarPlant, build_garden_ics
from waterleaf.models import WateringEvent


def test_calendar_contains_timed_events_alarm_profile_and_attachment():
    plant = CalendarPlant(
        id="plant-1",
        nickname="Front rose",
        common_name="Dog rose",
        scientific_name="Rosa canina",
        timezone="Europe/Stockholm",
        preferred_time=time(7, 30),
        profile_url="https://waterleaf.example/plants/rose-abc",
        image_url="https://waterleaf.example/media/image-1",
        events=[
            WateringEvent(
                date=date(2026, 6, 12),
                reason="Deferred after forecast rain",
                confidence="forecast",
            )
        ],
    )

    content = build_garden_ics([plant], generated_at="20260608T100000Z")

    assert "X-WR-CALNAME:Waterleaf" in content
    assert "SUMMARY:Water Front rose" in content
    assert "DTSTART;TZID=Europe/Stockholm:20260612T073000" in content
    assert "DTEND;TZID=Europe/Stockholm:20260612T074500" in content
    assert "TRIGGER:-PT30M" in content
    assert "URL:https://waterleaf.example/plants/rose-abc" in content
    assert "ATTACH;FMTTYPE=image/jpeg:https://waterleaf.example/media/image-1" in content
    assert "Dog rose (Rosa canina)" in content


def test_calendar_uid_is_stable_for_same_plant_and_date():
    plant = CalendarPlant(
        id="plant-1",
        nickname="Mint",
        common_name="Spearmint",
        scientific_name="Mentha spicata",
        timezone="UTC",
        preferred_time=time(8, 0),
        profile_url="https://example.com/plants/mint",
        image_url="https://example.com/media/mint",
        events=[
            WateringEvent(
                date=date(2026, 6, 12),
                reason="Species care baseline",
                confidence="baseline",
            )
        ],
    )

    first = build_garden_ics([plant], generated_at="20260608T100000Z")
    second = build_garden_ics([plant], generated_at="20260609T100000Z")

    first_uid = next(line for line in first.splitlines() if line.startswith("UID:"))
    second_uid = next(line for line in second.splitlines() if line.startswith("UID:"))
    assert first_uid == second_uid


def test_calendar_escapes_text_and_folds_long_lines():
    plant = CalendarPlant(
        id="plant-2",
        nickname="Herbs, north bed",
        common_name="A very long common plant name used to force an RFC line fold",
        scientific_name="Mentha longifolia",
        timezone="UTC",
        preferred_time=time(9, 0),
        profile_url="https://example.com/plants/" + ("very-long-segment-" * 8),
        image_url="https://example.com/media/image-2",
        events=[
            WateringEvent(
                date=date(2026, 6, 14),
                reason="Line one\nLine two; check",
                confidence="seasonal",
            )
        ],
    )

    content = build_garden_ics([plant], generated_at="20260608T100000Z")

    assert "SUMMARY:Water Herbs\\, north bed" in content
    assert "Line one\\nLine two\\; check" in content.replace("\r\n ", "")
    for line in content.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75

