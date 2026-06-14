from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_directory: Path
    public_base_url: str
    modal_endpoint: str | None
    modal_key: str | None
    modal_secret: str | None

    @property
    def database_path(self) -> Path:
        return self.data_directory / "waterleaf.sqlite3"

    @property
    def media_directory(self) -> Path:
        return self.data_directory / "media"

    @property
    def export_directory(self) -> Path:
        return self.data_directory / "exports"

    @classmethod
    def from_env(cls) -> Settings:
        data_directory = Path(os.getenv("WATERLEAF_DATA_DIR", "data"))
        public_base_url = os.getenv("PUBLIC_BASE_URL")
        if not public_base_url:
            space_host = os.getenv("SPACE_HOST")
            public_base_url = (
                f"https://{space_host}" if space_host else "http://localhost:7860"
            )
        return cls(
            data_directory=data_directory,
            public_base_url=public_base_url.rstrip("/"),
            modal_endpoint=os.getenv("MODAL_ENDPOINT"),
            modal_key=os.getenv("MODAL_KEY"),
            modal_secret=os.getenv("MODAL_SECRET"),
        )
