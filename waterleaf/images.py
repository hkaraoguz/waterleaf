from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

MAX_IMAGE_EDGE = 1600


@dataclass(frozen=True)
class StoredImage:
    id: str
    path: Path
    width: int
    height: int


def normalize_plant_image(
    source_path: str | Path,
    media_directory: str | Path,
) -> StoredImage:
    media_path = Path(media_directory)
    media_path.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as source:
        normalized = ImageOps.exif_transpose(source).convert("RGB")
        normalized.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
        width, height = normalized.size
        buffer = io.BytesIO()
        normalized.save(buffer, format="JPEG", quality=88, optimize=True)

    content = buffer.getvalue()
    image_id = hashlib.sha256(content).hexdigest()[:32]
    destination = media_path / f"{image_id}.jpg"
    if not destination.exists():
        destination.write_bytes(content)
    return StoredImage(id=image_id, path=destination, width=width, height=height)

