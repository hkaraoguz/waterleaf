from __future__ import annotations

import json
import secrets
import shutil
import sqlite3
import threading
import uuid
from datetime import time
from pathlib import Path
from typing import Any

from waterleaf.models import PlantDraft, PublicPlant, SavedPlant


class GardenStore:
    def __init__(self, database_path: str | Path, *, snapshot_path: str | Path | None = None):
        self.database_path = Path(database_path)
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self._lock = threading.RLock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        if self.snapshot_path and self.snapshot_path.exists() and not self.database_path.exists():
            shutil.copy2(self.snapshot_path, self.database_path)
        self._initialize()
        self._sync_snapshot()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS plants (
                        id TEXT PRIMARY KEY,
                        owner TEXT NOT NULL,
                        public_slug TEXT NOT NULL UNIQUE,
                        nickname TEXT NOT NULL,
                        common_name TEXT NOT NULL,
                        scientific_name TEXT NOT NULL,
                        taxon_key TEXT NOT NULL,
                        location_name TEXT NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        timezone TEXT NOT NULL,
                        preferred_time TEXT NOT NULL,
                        is_container INTEGER NOT NULL,
                        size_label TEXT NOT NULL,
                        image_id TEXT NOT NULL,
                        care_min_days INTEGER,
                        care_max_days INTEGER,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_plants_owner ON plants(owner);

                    CREATE TABLE IF NOT EXISTS schedules (
                        plant_id TEXT PRIMARY KEY,
                        owner TEXT NOT NULL,
                        events_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
                    );
                    """
                )

    def _sync_snapshot(self) -> None:
        if not self.snapshot_path:
            return
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.database_path, self.snapshot_path)

    def save_plant(self, owner: str, draft: PlantDraft) -> SavedPlant:
        with self._lock:
            plant_id = str(uuid.uuid4())
            public_slug = secrets.token_urlsafe(18)
            values = (
                plant_id,
                owner,
                public_slug,
                draft.nickname.strip(),
                draft.common_name.strip(),
                draft.scientific_name.strip(),
                draft.taxon_key,
                draft.location_name.strip(),
                round(draft.latitude, 2),
                round(draft.longitude, 2),
                draft.timezone,
                draft.preferred_time.isoformat(timespec="minutes"),
                int(draft.is_container),
                draft.size_label,
                draft.image_id,
                draft.care_min_days,
                draft.care_max_days,
            )
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO plants (
                        id, owner, public_slug, nickname, common_name, scientific_name,
                        taxon_key, location_name, latitude, longitude, timezone,
                        preferred_time, is_container, size_label, image_id,
                        care_min_days, care_max_days
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self._sync_snapshot()
            plant = self.get_plant(owner, plant_id)
        if plant is None:
            raise RuntimeError("Saved plant could not be loaded")
        return plant

    def list_plants(self, owner: str) -> list[SavedPlant]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM plants WHERE owner = ? ORDER BY created_at, id",
                    (owner,),
                ).fetchall()
        return [self._plant_from_row(row) for row in rows]

    def get_plant(self, owner: str, plant_id: str) -> SavedPlant | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM plants WHERE owner = ? AND id = ?",
                    (owner, plant_id),
                ).fetchone()
        return self._plant_from_row(row) if row else None

    def get_public_plant(self, public_slug: str) -> PublicPlant | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT public_slug, nickname, common_name, scientific_name,
                           image_id, is_container, size_label, care_min_days,
                           care_max_days
                    FROM plants WHERE public_slug = ?
                    """,
                    (public_slug,),
                ).fetchone()
        if not row:
            return None
        return PublicPlant(
            public_slug=row["public_slug"],
            nickname=row["nickname"],
            common_name=row["common_name"],
            scientific_name=row["scientific_name"],
            image_id=row["image_id"],
            is_container=bool(row["is_container"]),
            size_label=row["size_label"],
            care_min_days=row["care_min_days"],
            care_max_days=row["care_max_days"],
        )

    def delete_plant(self, owner: str, plant_id: str) -> bool:
        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM plants WHERE owner = ? AND id = ?",
                    (owner, plant_id),
                )
            deleted = cursor.rowcount == 1
            if deleted:
                self._sync_snapshot()
        return deleted

    def image_reference_count(self, image_id: str) -> int:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT COUNT(*) AS count FROM plants WHERE image_id = ?",
                    (image_id,),
                ).fetchone()
        return int(row["count"])

    def replace_schedule(
        self,
        owner: str,
        plant_id: str,
        events: list[dict[str, Any]],
    ) -> None:
        with self._lock:
            if self.get_plant(owner, plant_id) is None:
                raise PermissionError("Plant not found for owner")
            payload = json.dumps(events, separators=(",", ":"), sort_keys=True)
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO schedules (plant_id, owner, events_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(plant_id) DO UPDATE SET
                        owner = excluded.owner,
                        events_json = excluded.events_json,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (plant_id, owner, payload),
                )
            self._sync_snapshot()

    def get_schedule(self, owner: str, plant_id: str) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT events_json FROM schedules WHERE owner = ? AND plant_id = ?",
                    (owner, plant_id),
                ).fetchone()
        return json.loads(row["events_json"]) if row else []

    def get_public_schedule(self, public_slug: str) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT schedules.events_json
                    FROM schedules
                    JOIN plants ON plants.id = schedules.plant_id
                    WHERE plants.public_slug = ?
                    """,
                    (public_slug,),
                ).fetchone()
        return json.loads(row["events_json"]) if row else []

    @staticmethod
    def _plant_from_row(row: sqlite3.Row) -> SavedPlant:
        return SavedPlant(
            id=row["id"],
            owner=row["owner"],
            public_slug=row["public_slug"],
            nickname=row["nickname"],
            common_name=row["common_name"],
            scientific_name=row["scientific_name"],
            taxon_key=row["taxon_key"],
            location_name=row["location_name"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            timezone=row["timezone"],
            preferred_time=time.fromisoformat(row["preferred_time"]),
            is_container=bool(row["is_container"]),
            size_label=row["size_label"],
            image_id=row["image_id"],
            care_min_days=row["care_min_days"],
            care_max_days=row["care_max_days"],
        )
