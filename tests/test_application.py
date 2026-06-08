from datetime import date, time

from fastapi.testclient import TestClient
from PIL import Image

from waterleaf.application import WaterleafApplication
from waterleaf.models import CareProfile, LocationMatch, TaxonCandidate, WeatherDay
from waterleaf.storage import GardenStore
from waterleaf.web import create_web_app


class FakeCare:
    def get_care(self, scientific_name):
        return CareProfile(
            scientific_name=scientific_name,
            common_name="English lavender",
            min_days=7,
            max_days=9,
            watering_label="Minimum",
            sunlight=["full sun"],
        )


class FakeWeather:
    def geocode(self, query):
        assert query == "Stockholm"
        return LocationMatch(
            display_name="Stockholm, Sweden",
            latitude=59.33,
            longitude=18.07,
            timezone="Europe/Stockholm",
        )

    def forecast(self, latitude, longitude):
        return [
            WeatherDay(
                date=date(2026, 6, 16),
                precipitation_mm=7.0,
                max_temperature_c=20.0,
                et0_mm=2.0,
            )
        ]


def test_application_saves_plan_and_exports_whole_garden(tmp_path):
    source = tmp_path / "lavender.png"
    Image.new("RGB", (300, 500), color=(90, 120, 60)).save(source)
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    application = WaterleafApplication(
        store=store,
        media_directory=tmp_path / "media",
        export_directory=tmp_path / "exports",
        public_base_url="https://waterleaf.example",
        care=FakeCare(),
        weather=FakeWeather(),
    )
    candidate = TaxonCandidate(
        taxon_key="2925518",
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
        confidence=0.91,
        rationale="Purple spikes and narrow leaves",
    )

    plan = application.preview_schedule(
        candidate=candidate,
        location_query="Stockholm",
        is_container=True,
        size_label="medium",
        start=date(2026, 6, 8),
    )
    saved = application.save_plant(
        owner="alice",
        nickname="Patio lavender",
        candidate=candidate,
        source_image=source,
        preferred_time=time(7, 30),
        plan=plan,
    )
    exported = application.export_garden("alice", generated_at="20260608T100000Z")

    assert saved.image_id
    assert store.get_schedule("alice", saved.id)
    content = exported.read_text()
    unfolded = content.replace("\n ", "")
    assert "SUMMARY:Water Patio lavender" in content
    assert f"https://waterleaf.example/plants/{saved.public_slug}" in content
    assert f"https://waterleaf.example/media/{saved.image_id}.jpg" in unfolded


def test_public_profile_and_media_routes_exclude_private_location(tmp_path):
    source = tmp_path / "lavender.png"
    Image.new("RGB", (100, 100), color=(90, 120, 60)).save(source)
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    application = WaterleafApplication(
        store=store,
        media_directory=tmp_path / "media",
        export_directory=tmp_path / "exports",
        public_base_url="https://waterleaf.example",
        care=FakeCare(),
        weather=FakeWeather(),
    )
    candidate = TaxonCandidate(
        taxon_key="2925518",
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
    )
    plan = application.preview_schedule(
        candidate=candidate,
        location_query="Stockholm",
        is_container=True,
        size_label="medium",
        start=date(2026, 6, 8),
    )
    saved = application.save_plant(
        owner="alice",
        nickname="Patio lavender",
        candidate=candidate,
        source_image=source,
        preferred_time=time(7, 30),
        plan=plan,
    )
    client = TestClient(create_web_app(application, mount_ui=False))

    health = client.get("/health")
    profile = client.get(f"/plants/{saved.public_slug}")
    media = client.get(f"/media/{saved.image_id}.jpg")

    assert health.json() == {"status": "ok"}
    assert profile.status_code == 200
    assert "Patio lavender" in profile.text
    assert "Lavandula angustifolia" in profile.text
    assert "7-9 days" in profile.text
    assert "2026-06-" in profile.text
    assert "Stockholm" not in profile.text
    assert "alice" not in profile.text
    assert media.status_code == 200
    assert media.headers["content-type"] == "image/jpeg"
    assert client.get("/media/../../private.jpg").status_code == 404


def test_application_delete_removes_unreferenced_media(tmp_path):
    source = tmp_path / "lavender.png"
    Image.new("RGB", (100, 100), color=(90, 120, 60)).save(source)
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    application = WaterleafApplication(
        store=store,
        media_directory=tmp_path / "media",
        export_directory=tmp_path / "exports",
        public_base_url="https://waterleaf.example",
        care=FakeCare(),
        weather=FakeWeather(),
    )
    candidate = TaxonCandidate(
        taxon_key="2925518",
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
    )
    plan = application.preview_schedule(
        candidate=candidate,
        location_query="Stockholm",
        is_container=True,
        size_label="medium",
        start=date(2026, 6, 8),
    )
    first = application.save_plant(
        owner="alice",
        nickname="Patio lavender",
        candidate=candidate,
        source_image=source,
        preferred_time=time(7, 30),
        plan=plan,
    )
    second = application.save_plant(
        owner="alice",
        nickname="Second lavender",
        candidate=candidate,
        source_image=source,
        preferred_time=time(7, 30),
        plan=plan,
    )
    media_path = application.media_directory / f"{first.image_id}.jpg"

    assert first.image_id == second.image_id
    assert media_path.exists()
    assert application.delete_plant("alice", first.id) is True
    assert media_path.exists()
    assert application.delete_plant("alice", second.id) is True
    assert not media_path.exists()
