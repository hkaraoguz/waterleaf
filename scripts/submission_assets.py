from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080

END_CARD_LEAF_MARK_ORIGIN = (156, 170)
END_CARD_TITLE_BOX = (418, 232, 736, 352)

VOICEOVER = (
    "A garden photo should become something useful. Waterleaf uses Gemma 4 through llama.cpp "
    "to read visible traits, then grounds its suggestions in GBIF records so you make the final "
    "call. It combines local care baselines with weather rules to create an editable thirty-day "
    "plan. Save the plant, export the calendar, and every reminder links back to the photo. "
    "Built with Gradio, llama.cpp, and Modal."
)


@dataclass(frozen=True)
class CaptionCue:
    start: str
    end: str
    text: str


CAPTION_CUES = [
    CaptionCue("00:00:00,000", "00:00:04,000", "A garden photo should become something useful."),
    CaptionCue(
        "00:00:04,000",
        "00:00:11,000",
        "Waterleaf uses Gemma 4 through llama.cpp\n"
        "to read visible traits, then grounds its\n"
        "suggestions in GBIF records...",
    ),
    CaptionCue(
        "00:00:11,000",
        "00:00:19,000",
        "...so you make the final call. It combines\n"
        "local care baselines with weather rules to\n"
        "create an editable thirty-day plan.",
    ),
    CaptionCue(
        "00:00:19,000",
        "00:00:26,000",
        "Save the plant, export the calendar,\n"
        "and every reminder links back to the photo.",
    ),
    CaptionCue("00:00:26,000", "00:00:30,000", "Built with Gradio, llama.cpp, and Modal."),
]

END_CARD_LINES = [
    "Gemma 4 GGUF  |  llama.cpp  |  Modal  |  Gradio",
    "Backyard AI  |  Llama Champion  |  Field Notes",
    "hf.co/spaces/build-small-hackathon/waterleaf",
    "AI-generated narration",
]

THUMBNAIL_DETAIL = "Gemma vision, care rules, and weather-aware planning."


def speech_payload() -> dict[str, str]:
    return {
        "model": "gpt-4o-mini-tts-2025-12-15",
        "voice": "marin",
        "input": VOICEOVER,
        "response_format": "mp3",
        "instructions": (
            "calm, concise, confident, product-demo style; target 27 to 29 seconds; "
            "natural pace; emphasize `something useful`, `final call`, `thirty-day plan`, "
            "and `links back to the photo`; Do not add or remove words."
        ),
    }


def render_srt() -> str:
    blocks = []
    for index, cue in enumerate(CAPTION_CUES, start=1):
        blocks.append(f"{index}\n{cue.start} --> {cue.end}\n{cue.text}")
    return "\n\n".join(blocks) + "\n"


def generate_voiceover(
    destination: str | Path,
    api_key: str,
    client: httpx.Client | None = None,
) -> Path:
    own_client = client is None
    client = client or httpx.Client()
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}"},
            json=speech_payload(),
            timeout=120,
        )
        response.raise_for_status()
        destination_path.write_bytes(response.content)
        return destination_path
    finally:
        if own_client:
            client.close()


def _font_candidates(bold: bool = False) -> list[Path]:
    regular_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    bold_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    return bold_candidates if bold else regular_candidates


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = _font_candidates(bold=bold)
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    spacing: int = 10,
) -> tuple[int, int, int, int]:
    if "\n" in text:
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    else:
        bbox = draw.textbbox((0, 0), text, font=font)
    return bbox


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    start_size: int,
    min_size: int = 18,
    bold: bool = False,
    spacing: int = 10,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(size, bold=bold)
        bbox = _measure_text(draw, text, font, spacing=spacing)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width and height <= max_height:
            return font
    return _load_font(min_size, bold=bold)


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: str,
    start_size: int,
    min_size: int = 18,
    bold: bool = False,
    center: bool = False,
    spacing: int = 10,
) -> None:
    left, top, right, bottom = box
    font = _fit_font(
        draw,
        text,
        right - left,
        bottom - top,
        start_size=start_size,
        min_size=min_size,
        bold=bold,
        spacing=spacing,
    )
    bbox = _measure_text(draw, text, font, spacing=spacing)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (
        left + (right - left - width) / 2 - bbox[0]
        if center
        else left - bbox[0]
    )
    y = top + (bottom - top - height) / 2 - bbox[1]
    if "\n" in text:
        draw.multiline_text(
            (x, y),
            text,
            font=font,
            fill=fill,
            spacing=spacing,
            align="center" if center else "left",
        )
    else:
        draw.text((x, y), text, font=font, fill=fill)


def _leaf_mark_bounds(origin: tuple[int, int]) -> tuple[int, int, int, int]:
    x, y = origin
    left = x
    top = y + 52
    right = x + 120 + int(140 * 0.68)
    bottom = y + 170
    return left, top, right, bottom


END_CARD_LEAF_MARK_BOUNDS = _leaf_mark_bounds(END_CARD_LEAF_MARK_ORIGIN)
END_CARD_LEAF_MARK_BOX = END_CARD_LEAF_MARK_BOUNDS


def _create_canvas() -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), "#173024")


def _draw_background(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill="#173024")
    draw.rounded_rectangle(
        [84, 84, WIDTH - 84, HEIGHT - 84],
        radius=46,
        fill="#f6f0e4",
        outline="#c7b89a",
        width=4,
    )
    draw.ellipse([-220, -220, 520, 540], fill="#254b36")
    draw.ellipse([WIDTH - 520, 116, WIDTH + 120, 760], fill="#d7e4cf")
    draw.ellipse([WIDTH - 290, 826, WIDTH + 120, HEIGHT + 160], fill="#89a97b")


def _draw_leaf_mark(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    accent = "#6da66a"
    outline = "#2f5a3e"
    for offset, scale in ((0, 1.0), (62, 0.82), (120, 0.68)):
        box = [x + offset, y + 52, x + offset + int(140 * scale), y + 170]
        draw.ellipse(box, fill=accent, outline=outline, width=3)
        draw.line(
            [
                (box[0] + 18, (box[1] + box[3]) / 2),
                (box[2] - 16, (box[1] + box[3]) / 2),
            ],
            fill=outline,
            width=4,
        )
        draw.polygon(
            [
                (box[0] + 48, box[1] + 26),
                (box[0] + 82, box[1] + 16),
                (box[0] + 105, box[1] + 40),
                (box[0] + 82, box[1] + 64),
            ],
            fill="#93c38c",
        )


def render_end_card() -> Image.Image:
    image = _create_canvas()
    draw = ImageDraw.Draw(image)
    _draw_background(draw)

    draw.rounded_rectangle(
        [128, 132, 820, 944],
        radius=36,
        fill="#173024",
        outline="#6da66a",
        width=3,
    )
    draw.rounded_rectangle(
        [880, 132, 1792, 944],
        radius=36,
        fill="#dbe7d2",
        outline="#b8c9ae",
        width=3,
    )
    _draw_leaf_mark(draw, END_CARD_LEAF_MARK_ORIGIN)

    _draw_fitted_text(
        draw,
        END_CARD_TITLE_BOX,
        "Waterleaf",
        fill="#f6f0e4",
        start_size=80,
        min_size=58,
        bold=True,
    )
    _draw_fitted_text(
        draw,
        (206, 350, 734, 414),
        "Photo to plant care",
        fill="#d7e4cf",
        start_size=42,
        min_size=28,
    )
    _draw_fitted_text(
        draw,
        (206, 450, 722, 514),
        "Visible traits, GBIF context,",
        fill="#d7e4cf",
        start_size=32,
        min_size=24,
    )
    _draw_fitted_text(
        draw,
        (206, 500, 748, 564),
        "and weather rules in one plan.",
        fill="#d7e4cf",
        start_size=32,
        min_size=24,
    )

    _draw_fitted_text(
        draw,
        (928, 194, 1712, 282),
        "AI garden demo",
        fill="#173024",
        start_size=54,
        min_size=36,
        bold=True,
    )
    _draw_fitted_text(
        draw,
        (928, 304, 1656, 364),
        "Editable care plan from a photo.",
        fill="#2f5a3e",
        start_size=32,
        min_size=24,
    )
    _draw_fitted_text(
        draw,
        (928, 374, 1692, 434),
        "Grounded in local baselines and weather.",
        fill="#2f5a3e",
        start_size=30,
        min_size=22,
    )

    draw.rounded_rectangle(
        [172, 760, 1740, 942],
        radius=26,
        fill="#f6f0e4",
        outline="#c7b89a",
        width=3,
    )
    footer_rows = [
        (END_CARD_LINES[0], (208, 786, 1704, 826), 30),
        (END_CARD_LINES[1], (208, 830, 1704, 868), 30),
        (END_CARD_LINES[2], (208, 872, 1704, 900), 24),
        (END_CARD_LINES[3], (208, 902, 1704, 932), 22),
    ]
    for text, box, size in footer_rows:
        _draw_fitted_text(
            draw,
            box,
            text,
            fill="#173024",
            start_size=size,
            min_size=18,
            center=True,
            bold=text == END_CARD_LINES[0],
        )
    return image


def render_thumbnail() -> Image.Image:
    image = _create_canvas()
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill="#223f2f")
    draw.rounded_rectangle([78, 78, WIDTH - 78, HEIGHT - 78], radius=52, fill="#f7f2e8")
    draw.rounded_rectangle([120, 120, 760, 960], radius=44, fill="#173024")
    draw.rounded_rectangle([820, 120, WIDTH - 120, 960], radius=44, fill="#dbe7d2")
    _draw_leaf_mark(draw, (178, 198))

    _draw_fitted_text(
        draw,
        (170, 500, 694, 620),
        "Waterleaf",
        fill="#f6f0e4",
        start_size=100,
        min_size=70,
        bold=True,
    )
    _draw_fitted_text(
        draw,
        (170, 630, 680, 700),
        "Photo to plant plan",
        fill="#d7e4cf",
        start_size=44,
        min_size=32,
    )

    draw.rounded_rectangle([168, 758, 652, 862], radius=26, fill="#6da66a")
    _draw_fitted_text(
        draw,
        (196, 780, 628, 840),
        "Gemma 4 + GBIF + Weather",
        fill="#173024",
        start_size=32,
        min_size=22,
        center=True,
        bold=True,
    )

    _draw_fitted_text(
        draw,
        (864, 196, 1660, 282),
        "AI garden demo",
        fill="#173024",
        start_size=58,
        min_size=38,
        bold=True,
    )
    _draw_fitted_text(
        draw,
        (864, 312, 1640, 366),
        "Editable care plan from a single photo.",
        fill="#2f5a3e",
        start_size=32,
        min_size=24,
    )
    _draw_fitted_text(
        draw,
        (864, 376, 1644, 430),
        "Visible traits, local baselines, and weather.",
        fill="#2f5a3e",
        start_size=30,
        min_size=22,
    )
    draw.rounded_rectangle(
        [864, 486, 1656, 808],
        radius=36,
        outline="#89a97b",
        width=5,
        fill="#f6f0e4",
    )
    _draw_fitted_text(
        draw,
        (914, 548, 1606, 628),
        "Suggestion engine",
        fill="#173024",
        start_size=40,
        min_size=28,
        bold=True,
    )
    _draw_fitted_text(
        draw,
        (914, 642, 1582, 724),
        THUMBNAIL_DETAIL,
        fill="#173024",
        start_size=30,
        min_size=20,
    )
    return image


def write_static_assets(output_directory: str | Path) -> dict[str, Path]:
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)

    script_path = output_path / "waterleaf-voiceover.txt"
    captions_path = output_path / "waterleaf-demo.srt"
    end_card_path = output_path / "waterleaf-end-card.png"
    thumbnail_path = output_path / "waterleaf-thumbnail.png"

    script_path.write_text(VOICEOVER + "\n")
    captions_path.write_text(render_srt())
    render_end_card().save(end_card_path)
    render_thumbnail().save(thumbnail_path)

    return {
        "script": script_path,
        "captions": captions_path,
        "end_card": end_card_path,
        "thumbnail": thumbnail_path,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate Waterleaf hackathon submission assets.")
    parser.add_argument("--out", type=Path, default=Path("artifacts/submission"))
    parser.add_argument("--voice", action="store_true")
    args = parser.parse_args(argv)

    if args.voice and not os.getenv("OPENAI_API_KEY"):
        parser.error("--voice requires OPENAI_API_KEY")

    outputs = write_static_assets(args.out)
    for name, path in outputs.items():
        print(f"{name}: {path}")

    if args.voice:
        api_key = os.getenv("OPENAI_API_KEY")
        voice_path = generate_voiceover(args.out / "waterleaf-voiceover.mp3", api_key)
        print(f"voice: {voice_path}")


if __name__ == "__main__":
    main()
