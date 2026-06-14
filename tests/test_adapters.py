import json
from pathlib import Path

import httpx
from PIL import Image

from waterleaf.models import TaxonCandidate, VisualAnalysis
from waterleaf.services.care import LocalCareCatalog
from waterleaf.services.gbif import GbifClient
from waterleaf.services.llama_cpp import VISUAL_SCHEMA, LlamaCppClient
from waterleaf.services.open_meteo import OpenMeteoClient


def test_gbif_suggest_returns_only_plant_species():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "lavender"
        assert request.url.path.endswith("/species/search")
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "key": 999,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "DOUBTFUL",
                        "canonicalName": "Lavandula angustifolia",
                    },
                    {
                        "key": 2925518,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "ACCEPTED",
                        "scientificName": "Lavandula angustifolia Mill.",
                        "canonicalName": "Lavandula angustifolia",
                        "vernacularNames": [
                            {
                                "vernacularName": "English lavender",
                                "language": "eng",
                            }
                        ],
                    },
                    {
                        "key": 1,
                        "rank": "GENUS",
                        "kingdom": "Plantae",
                        "scientificName": "Lavandula",
                    },
                    {
                        "key": 2,
                        "rank": "SPECIES",
                        "kingdom": "Animalia",
                        "scientificName": "Lavandula mimic",
                    },
                ]
            },
        )

    client = GbifClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.suggest("lavender")[0].model_dump() == {
        "taxon_key": "2925518",
        "scientific_name": "Lavandula angustifolia",
        "common_name": "English lavender",
        "confidence": 0.0,
        "rationale": "",
    }


def test_gbif_prioritizes_exact_common_name_and_accepted_taxa():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "key": 10,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "ACCEPTED",
                        "canonicalName": "Lonchitis hirsuta",
                        "vernacularNames": [
                            {"vernacularName": "Tomato fern", "language": "eng"}
                        ],
                    },
                    {
                        "key": 20,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "ACCEPTED",
                        "canonicalName": "Solanum lycopersicum",
                        "vernacularNames": [
                            {"vernacularName": "Garden tomato", "language": "eng"},
                            {"vernacularName": "Tomato", "language": "eng"},
                        ],
                    },
                ]
            },
        )

    client = GbifClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    matches = client.suggest("tomato")

    assert matches[0].scientific_name == "Solanum lycopersicum"
    assert matches[0].common_name == "Tomato"


def test_gbif_scientific_search_prefers_accepted_record_with_common_name():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "key": 10,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "DOUBTFUL",
                        "canonicalName": "Lavandula angustifolia",
                    },
                    {
                        "key": 20,
                        "rank": "SPECIES",
                        "kingdom": "Plantae",
                        "taxonomicStatus": "ACCEPTED",
                        "canonicalName": "Lavandula angustifolia",
                        "vernacularNames": [
                            {
                                "vernacularName": "English lavender",
                                "language": "eng",
                            }
                        ],
                    },
                ]
            },
        )

    client = GbifClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    matches = client.suggest("Lavandula angustifolia")

    assert matches[0].taxon_key == "20"
    assert matches[0].common_name == "English lavender"


def test_local_care_catalog_matches_species_with_author_suffix():
    profile = LocalCareCatalog().get_care("Lavandula angustifolia Mill.")

    assert profile.scientific_name == "Lavandula angustifolia Mill."
    assert profile.common_name == "English lavender"
    assert profile.min_days == 7
    assert profile.max_days == 10
    assert profile.sunlight == ["full sun"]


def test_local_care_catalog_uses_lavender_genus_baseline():
    profile = LocalCareCatalog().get_care("Lavandula latifolia Medik.")

    assert profile.common_name == "Lavender"
    assert profile.min_days == 7
    assert profile.max_days == 10


def test_local_care_catalog_requires_manual_interval_for_unknown_species():
    profile = LocalCareCatalog().get_care("Tulipa gesneriana")

    assert profile.common_name == "Tulipa gesneriana"
    assert profile.min_days is None
    assert profile.max_days is None


def test_open_meteo_geocodes_and_parses_forecast():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Stockholm",
                            "country": "Sweden",
                            "latitude": 59.33,
                            "longitude": 18.07,
                            "timezone": "Europe/Stockholm",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "timezone": "Europe/Stockholm",
                "daily": {
                    "time": ["2026-06-08", "2026-06-09"],
                    "precipitation_sum": [0.0, 7.2],
                    "temperature_2m_max": [22.0, 19.0],
                    "et0_fao_evapotranspiration": [3.1, 1.4],
                },
            },
        )

    client = OpenMeteoClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    location = client.geocode("Stockholm")
    forecast = client.forecast(location.latitude, location.longitude)

    assert location.display_name == "Stockholm, Sweden"
    assert location.timezone == "Europe/Stockholm"
    assert forecast[1].precipitation_mm == 7.2


def test_open_meteo_uses_seasonal_schedule_when_forecast_is_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    client = OpenMeteoClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.forecast(59.33, 18.07) == []


def test_llama_cpp_sends_all_images_and_constrained_schema(tmp_path):
    image_paths: list[Path] = []
    for index in range(2):
        path = tmp_path / f"plant-{index}.jpg"
        Image.new("RGB", (20, 20), color=(30 + index, 120, 40)).save(path)
        image_paths.append(path)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "traits": ["purple flower spikes"],
                                    "proposed_names": ["Lavandula angustifolia"],
                                    "is_container": True,
                                    "size_label": "medium",
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = LlamaCppClient(
        endpoint="https://modal.example",
        modal_key="key",
        modal_secret="secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = client.analyze_images(image_paths)

    content = captured["messages"][1]["content"]
    assert len([part for part in content if part["type"] == "image_url"]) == 2
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"] == {
        "name": "visual_analysis",
        "schema": VISUAL_SCHEMA,
        "strict": True,
    }
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}
    assert result.proposed_names == ["Lavandula angustifolia"]
    assert result.is_container is True


def test_llama_cpp_enables_thinking_for_candidate_reranking():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "ranking": [
                                        {
                                            "taxon_key": "2925518",
                                            "confidence": 0.92,
                                            "rationale": "Flower and leaf morphology match.",
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = LlamaCppClient(
        endpoint="https://modal.example",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    ranking = client.rerank(
        [],
        VisualAnalysis(
            traits=["purple flower spikes"],
            proposed_names=["Lavandula angustifolia"],
            is_container=True,
            size_label="medium",
        ),
        [
            TaxonCandidate(
                taxon_key="2925518",
                scientific_name="Lavandula angustifolia",
                common_name="English lavender",
            )
        ],
    )

    assert captured["chat_template_kwargs"] == {"enable_thinking": True}
    assert ranking[0]["taxon_key"] == "2925518"
