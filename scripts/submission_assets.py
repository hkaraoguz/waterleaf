from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080

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


def speech_payload() -> dict[str, str]:
    return {
        "model": "gpt-4o-mini-tts-2025-12-15",
        "voice": "marin",
        "input": VOICEOVER,
        "response_format": "mp3",
        "instructions": (
            "calm concise confident product-demo style; target 27 to 29 seconds; "
            "natural pace; emphasize `something useful`, `final call`, `thirty-day plan`, "
            "`links back to the photo`; Do not add or remove words."
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


def _font_candidates() -> list[Path]:
    return [
        Path("/Library/Fonts/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = _font_candidates()
    if bold:
        candidates = [path for path in candidates if "Bold" in path.name] + [
            path for path in candidates if "Bold" not in path.name
        ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _create_canvas() -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), "#173024")


def _draw_background(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill="#173024")
    draw.rounded_rectangle(
        [96, 96, WIDTH - 96, HEIGHT - 96],
        radius=42,
        fill="#f6f0e4",
        outline="#c7b89a",
        width=4,
    )
    draw.ellipse([-220, -180, 680, 740], fill="#254b36")
    draw.ellipse([WIDTH - 580, 110, WIDTH + 180, 870], fill="#d7e4cf")
    draw.ellipse([WIDTH - 430, 760, WIDTH + 110, HEIGHT + 190], fill="#89a97b")


def _multiline_center(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    spacing: int = 12,
) -> None:
    left, top, right, bottom = box
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing, align="center")


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

    title_font = _load_font(68, bold=True)
    body_font = _load_font(38)
    url_font = _load_font(30)
    footer_font = _load_font(24)

    draw.rounded_rectangle(
        [144, 160, 1100, 610],
        radius=38,
        fill="#173024",
        outline="#6da66a",
        width=3,
    )
    _draw_leaf_mark(draw, (210, 210))

    draw.text((420, 240), "Waterleaf", font=title_font, fill="#f6f0e4")
    draw.text((420, 336), "Plant care that starts from a photo.", font=body_font, fill="#d7e4cf")
    draw.text(
        (420, 414),
        "Identifies visible traits, grounds suggestions in GBIF, and builds",
        font=body_font,
        fill="#d7e4cf",
    )
    draw.text(
        (420, 464),
        "an editable 30-day plan you can export and use immediately.",
        font=body_font,
        fill="#d7e4cf",
    )

    draw.rounded_rectangle(
        [116, 770, WIDTH - 116, 912],
        radius=30,
        fill="#f6f0e4",
        outline="#c7b89a",
        width=3,
    )
    _multiline_center(
        draw,
        (150, 790, WIDTH - 150, 892),
        "\n".join(END_CARD_LINES[:2]),
        body_font,
        fill="#173024",
        spacing=14,
    )
    draw.text((WIDTH / 2 - 410, 878), END_CARD_LINES[2], font=url_font, fill="#2f5a3e")
    draw.text((WIDTH / 2 - 180, 916), END_CARD_LINES[3], font=footer_font, fill="#6b5c45")
    return image


def render_thumbnail() -> Image.Image:
    image = _create_canvas()
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill="#223f2f")
    draw.rounded_rectangle([78, 78, WIDTH - 78, HEIGHT - 78], radius=52, fill="#f7f2e8")
    draw.rounded_rectangle([120, 120, 820, 960], radius=44, fill="#173024")
    draw.rounded_rectangle([876, 120, WIDTH - 120, 960], radius=44, fill="#dbe7d2")
    _draw_leaf_mark(draw, (178, 198))

    title_font = _load_font(96, bold=True)
    subtitle_font = _load_font(46)
    badge_font = _load_font(32, bold=True)
    small_font = _load_font(28)

    draw.text((178, 520), "Waterleaf", font=title_font, fill="#f6f0e4")
    draw.text((180, 648), "Photo to plant plan", font=subtitle_font, fill="#d7e4cf")

    draw.rounded_rectangle([180, 760, 620, 860], radius=26, fill="#6da66a")
    draw.text((228, 788), "Gemma 4 + GBIF + Weather", font=badge_font, fill="#173024")
    draw.text((930, 214), "AI garden demo", font=subtitle_font, fill="#173024")
    draw.text(
        (930, 314),
        "Editable care plan from a single photo.",
        font=small_font,
        fill="#2f5a3e",
    )
    draw.text(
        (930, 380),
        "Built for the Hackathon submission.",
        font=small_font,
        fill="#2f5a3e",
    )
    draw.rounded_rectangle(
        [930, 480, 1600, 808],
        radius=34,
        outline="#89a97b",
        width=5,
        fill="#f6f0e4",
    )
    draw.text((985, 554), "Suggestion engine", font=badge_font, fill="#173024")
    draw.text(
        (985, 625),
        "Local vision, care rules, and weather-aware planning.",
        font=small_font,
        fill="#173024",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Waterleaf hackathon submission assets.")
    parser.add_argument("--out", type=Path, default=Path("artifacts/submission"))
    parser.add_argument("--voice", action="store_true")
    args = parser.parse_args()

    outputs = write_static_assets(args.out)
    for name, path in outputs.items():
        print(f"{name}: {path}")

    if args.voice:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            parser.error("--voice requires OPENAI_API_KEY")
        voice_path = generate_voiceover(args.out / "waterleaf-voiceover.mp3", api_key)
        print(f"voice: {voice_path}")


if __name__ == "__main__":
    main()
