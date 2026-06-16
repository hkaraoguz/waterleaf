from datetime import time

from waterleaf.models import PlantDraft
from waterleaf.storage import GardenStore


def _draft() -> PlantDraft:
    return PlantDraft(
        nickname="Patio lavender",
        common_name="English lavender",
        scientific_name="Lavandula angustifolia",
        taxon_key="2925518",
        location_name="Stockholm, Sweden",
        latitude=59.32932,
        longitude=18.06858,
        timezone="Europe/Stockholm",
        preferred_time=time(7, 30),
        is_container=True,
        size_label="medium",
        image_id="image-1",
        care_min_days=7,
        care_max_days=10,
    )


def test_store_isolates_plants_by_owner(tmp_path):
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    plant = store.save_plant("alice", _draft())

    assert store.list_plants("alice") == [plant]
    assert store.list_plants("bob") == []
    assert store.get_plant("bob", plant.id) is None
    assert store.get_plant("alice", plant.id) == plant


def test_store_rounds_private_coordinates_and_exposes_safe_public_record(tmp_path):
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    plant = store.save_plant("alice", _draft())

    assert plant.latitude == 59.33
    assert plant.longitude == 18.07
    public = store.get_public_plant(plant.public_slug)

    assert public is not None
    assert public.nickname == "Patio lavender"
    assert public.scientific_name == "Lavandula angustifolia"
    assert not hasattr(public, "owner")
    assert not hasattr(public, "latitude")
    assert len(plant.public_slug) >= 20


def test_only_owner_can_delete_plant(tmp_path):
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    plant = store.save_plant("alice", _draft())

    assert store.delete_plant("bob", plant.id) is False
    assert store.get_plant("alice", plant.id) is not None
    assert store.delete_plant("alice", plant.id) is True
    assert store.get_public_plant(plant.public_slug) is None


def test_store_replaces_schedule_atomically(tmp_path):
    store = GardenStore(tmp_path / "waterleaf.sqlite3")
    plant = store.save_plant("alice", _draft())

    store.replace_schedule(
        "alice",
        plant.id,
        [
            {"date": "2026-06-12", "reason": "Forecast", "confidence": "forecast"},
            {"date": "2026-06-18", "reason": "Baseline", "confidence": "baseline"},
        ],
    )
    store.replace_schedule(
        "alice",
        plant.id,
        [{"date": "2026-06-14", "reason": "Edited", "confidence": "manual"}],
    )

    assert store.get_schedule("alice", plant.id) == [
        {"date": "2026-06-14", "reason": "Edited", "confidence": "manual"}
    ]


def test_store_uses_local_database_and_syncs_snapshot(tmp_path):
    snapshot_path = tmp_path / "bucket" / "waterleaf.sqlite3"
    seed_store = GardenStore(snapshot_path)
    seed = seed_store.save_plant("alice", _draft())
    seed_store.replace_schedule(
        "alice",
        seed.id,
        [{"date": "2026-06-14", "reason": "Seed", "confidence": "manual"}],
    )

    local_path = tmp_path / "local" / "waterleaf.sqlite3"
    store = GardenStore(local_path, snapshot_path=snapshot_path)
    saved = store.save_plant("alice", _draft())
    store.replace_schedule(
        "alice",
        saved.id,
        [{"date": "2026-06-15", "reason": "Synced", "confidence": "manual"}],
    )

    assert local_path.exists()
    assert store.get_schedule("alice", seed.id) == [
        {"date": "2026-06-14", "reason": "Seed", "confidence": "manual"}
    ]

    reloaded = GardenStore(
        tmp_path / "reloaded" / "waterleaf.sqlite3",
        snapshot_path=snapshot_path,
    )
    assert {plant.id for plant in reloaded.list_plants("alice")} == {seed.id, saved.id}
    assert reloaded.get_schedule("alice", saved.id) == [
        {"date": "2026-06-15", "reason": "Synced", "confidence": "manual"}
    ]
