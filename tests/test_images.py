from PIL import Image

from waterleaf.images import normalize_plant_image


def test_normalize_image_resizes_strips_exif_and_writes_jpeg(tmp_path):
    source = tmp_path / "source.jpg"
    image = Image.new("RGB", (2400, 1200), color=(70, 130, 70))
    exif = Image.Exif()
    exif[0x010E] = "private garden note"
    image.save(source, exif=exif)

    stored = normalize_plant_image(source, tmp_path / "media")

    assert stored.path.suffix == ".jpg"
    assert stored.width == 1600
    assert stored.height == 800
    with Image.open(stored.path) as normalized:
        assert normalized.getexif() == {}
        assert normalized.mode == "RGB"


def test_normalize_image_generates_stable_content_id(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (120, 80), color=(120, 80, 40)).save(source)

    first = normalize_plant_image(source, tmp_path / "media")
    second = normalize_plant_image(source, tmp_path / "media")

    assert first.id == second.id
    assert first.path == second.path

