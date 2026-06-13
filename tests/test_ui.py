import json

import pytest

from waterleaf.application import WaterleafApplication
from waterleaf.models import TaxonCandidate
from waterleaf.storage import GardenStore
from waterleaf.ui import _candidate_label, _parse_optional_interval, build_ui


class NoopCare:
    def get_care(self, scientific_name):
        raise AssertionError("Not called while building UI")


class NoopWeather:
    def geocode(self, query):
        raise AssertionError("Not called while building UI")

    def forecast(self, latitude, longitude):
        raise AssertionError("Not called while building UI")


class NoopIdentification:
    def identify(self, image_paths):
        raise AssertionError("Not called while building UI")


class NoopTaxonomy:
    def suggest(self, query, limit=10):
        return []


def test_ui_contains_dashboard_capture_confirmation_and_export(tmp_path):
    application = WaterleafApplication(
        store=GardenStore(tmp_path / "waterleaf.sqlite3"),
        media_directory=tmp_path / "media",
        export_directory=tmp_path / "exports",
        public_base_url="https://waterleaf.example",
        care=NoopCare(),
        weather=NoopWeather(),
    )

    demo = build_ui(
        application,
        identification=NoopIdentification(),
        taxonomy=NoopTaxonomy(),
        sample_image="assets/sample-lavender.png",
    )
    config_file = demo.get_config_file()
    config = json.dumps(config_file, default=str)

    assert "Waterleaf" in config
    assert "Add plant" in config
    assert "Analyze photos" in config
    assert "Confirm species" in config
    assert "Generate 30-day calendar" in config
    assert "Sign in with Hugging Face" in config
    assert "Plant photo (required)" in config
    assert "Database match (required)" in config
    assert "Plant nickname (required)" in config
    assert "City (required)" in config
    assert "Watering time (required)" in config
    assert "Custom watering interval (optional)" in config
    assert "Leave blank to use plant care data" in config
    assert "Example: 7" in config
    assert "Garden location" not in config
    assert "Interval override" not in config
    city = next(
        component
        for component in config_file["components"]
        if component.get("props", {}).get("label") == "City (required)"
    )
    assert city["props"]["value"] == "Stockholm, Sweden"


def test_ui_handlers_are_not_exposed_as_public_api(tmp_path):
    application = WaterleafApplication(
        store=GardenStore(tmp_path / "waterleaf.sqlite3"),
        media_directory=tmp_path / "media",
        export_directory=tmp_path / "exports",
        public_base_url="https://waterleaf.example",
        care=NoopCare(),
        weather=NoopWeather(),
    )

    demo = build_ui(
        application,
        identification=NoopIdentification(),
        taxonomy=NoopTaxonomy(),
        sample_image="assets/sample-lavender.png",
    )
    dependencies = demo.get_config_file()["dependencies"]

    assert dependencies
    assert all(item["api_visibility"] != "public" for item in dependencies)


def test_optional_watering_interval_accepts_blank_or_one_to_thirty_days():
    assert _parse_optional_interval("") is None
    assert _parse_optional_interval("7") == 7

    with pytest.raises(ValueError, match="whole number from 1 to 30"):
        _parse_optional_interval("0")
    with pytest.raises(ValueError, match="whole number from 1 to 30"):
        _parse_optional_interval("weekly")


def test_candidate_label_shows_common_and_scientific_names():
    candidate = TaxonCandidate(
        taxon_key="2927305",
        scientific_name="Lavandula angustifolia",
        common_name="English lavender",
        confidence=0.8,
    )
    unavailable = candidate.model_copy(
        update={"common_name": "Lavandula angustifolia"}
    )

    assert _candidate_label(candidate) == (
        "English lavender | Lavandula angustifolia | 80%"
    )
    assert _candidate_label(unavailable) == (
        "Lavandula angustifolia | Common name unavailable | 80%"
    )
