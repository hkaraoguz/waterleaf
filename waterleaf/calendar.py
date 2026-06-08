from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from waterleaf.models import WateringEvent


@dataclass(frozen=True)
class CalendarPlant:
    id: str
    nickname: str
    common_name: str
    scientific_name: str
    timezone: str
    preferred_time: time
    profile_url: str
    image_url: str
    events: list[WateringEvent]


def build_garden_ics(
    plants: list[CalendarPlant],
    *,
    generated_at: str | None = None,
) -> str:
    stamp = generated_at or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Waterleaf//Garden Watering Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Waterleaf",
    ]
    for plant in plants:
        for event in plant.events:
            lines.extend(_event_lines(plant, event, stamp))
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold_line(line) for line in lines) + "\r\n"


def _event_lines(
    plant: CalendarPlant,
    event: WateringEvent,
    stamp: str,
) -> list[str]:
    start_dt = datetime.combine(event.date, plant.preferred_time)
    end_dt = start_dt + timedelta(minutes=15)
    uid_seed = f"{plant.id}:{event.date.isoformat()}".encode()
    uid = hashlib.sha256(uid_seed).hexdigest()[:24]
    description = (
        f"{plant.common_name} ({plant.scientific_name})\n"
        f"{event.reason}\n"
        f"Plant profile: {plant.profile_url}"
    )
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}@waterleaf",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={plant.timezone}:{start_dt:%Y%m%dT%H%M%S}",
        f"DTEND;TZID={plant.timezone}:{end_dt:%Y%m%dT%H%M%S}",
        f"SUMMARY:{_escape_text(f'Water {plant.nickname}')}",
        f"DESCRIPTION:{_escape_text(description)}",
        f"URL:{plant.profile_url}",
        f"ATTACH;FMTTYPE=image/jpeg:{plant.image_url}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape_text(f'Water {plant.nickname}')}",
        "TRIGGER:-PT30M",
        "END:VALARM",
        "END:VEVENT",
    ]


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_line(line: str, limit: int = 75) -> str:
    encoded = line.encode("utf-8")
    if len(encoded) <= limit:
        return line

    chunks: list[str] = []
    remaining = line
    first = True
    while remaining:
        available = limit if first else limit - 1
        byte_count = 0
        split_at = 0
        for char in remaining:
            char_length = len(char.encode("utf-8"))
            if byte_count + char_length > available:
                break
            byte_count += char_length
            split_at += 1
        if split_at == 0:
            split_at = 1

        prefix = "" if first else " "
        chunks.append(prefix + remaining[:split_at])
        remaining = remaining[split_at:]
        first = False
    return "\r\n".join(chunks)
