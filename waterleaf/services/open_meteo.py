from __future__ import annotations

from datetime import date

import httpx

from waterleaf.models import LocationMatch, WeatherDay


class OpenMeteoClient:
    def __init__(self, *, http_client: httpx.Client | None = None):
        self.http_client = http_client or httpx.Client(timeout=15.0)

    def geocode(self, query: str) -> LocationMatch:
        response = self.http_client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            raise ValueError(f"Location not found: {query}")
        item = results[0]
        display = ", ".join(
            part for part in [item.get("name"), item.get("admin1"), item.get("country")] if part
        )
        return LocationMatch(
            display_name=display,
            latitude=item["latitude"],
            longitude=item["longitude"],
            timezone=item["timezone"],
        )

    def forecast(self, latitude: float, longitude: float) -> list[WeatherDay]:
        try:
            response = self.http_client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "daily": (
                        "precipitation_sum,temperature_2m_max,"
                        "et0_fao_evapotranspiration"
                    ),
                    "forecast_days": 16,
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            daily = response.json()["daily"]
            return [
                WeatherDay(
                    date=date.fromisoformat(day),
                    precipitation_mm=float(daily["precipitation_sum"][index] or 0),
                    max_temperature_c=float(daily["temperature_2m_max"][index] or 0),
                    et0_mm=float(daily["et0_fao_evapotranspiration"][index] or 0),
                )
                for index, day in enumerate(daily["time"])
            ]
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return []
