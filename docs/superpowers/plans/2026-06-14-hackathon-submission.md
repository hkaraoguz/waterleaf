# Waterleaf Hackathon Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify Waterleaf's 30-second LinkedIn demo, social post, Field Notes report, badge evidence, and final submission links before the June 15, 2026 deadline.

**Architecture:** Keep the deployed Waterleaf application unchanged. Add a small, tested submission-asset toolchain that generates the approved narration request, captions, end card, thumbnail, and deterministic FFmpeg composition command; record four short live-product clips manually and assemble them into the final video. Publish the report from the existing Hugging Face Space repository so every required link is public without adding another hosting dependency.

**Tech Stack:** Python 3.11+, `httpx`, Pillow, `imageio-ffmpeg`, pytest, Ruff, Hugging Face Spaces, LinkedIn native video, OpenAI Speech API, FFmpeg.

---

## Critical Path

Complete Tasks 1-7 in order. Required submission assets take priority over the
optional evaluation backlog.

1. Build and test deterministic submission asset generation.
2. Build and test deterministic video composition and validation.
3. Replace all draft publication copy with approved final copy.
4. Add the licensed sample image and lock technical evidence.
5. Capture the four live product clips.
6. Generate narration, assemble, and QA the 30-second video.
7. publish the Space report, publish the LinkedIn post, and submit the URLs.

Do not begin a 20-image evaluation set, offline architecture work, or product
refactoring until the required Space, video, LinkedIn post, and Field Notes are
public.

## File Map

### Create

- `scripts/submission_assets.py`
  - Owns the approved voiceover text, SRT cues, OpenAI speech request, end card,
    and thumbnail generation.
- `scripts/compose_demo.py`
  - Owns the five-beat FFmpeg timeline, codec settings, media probing, and final
    duration/codec validation.
- `tests/test_submission_assets.py`
  - Verifies script text, caption timing, speech payload, API output handling,
    and image dimensions.
- `tests/test_compose_demo.py`
  - Verifies timeline inputs, FFmpeg filters/codecs, media parsing, and
    validation failures.
- `assets/demo/lavender-garden-brooke-balentine.jpg`
  - Licensed Unsplash image used as the real garden sample.
- `assets/demo/ATTRIBUTION.md`
  - Source and license record for the sample image.
- `docs/submission-evidence.md`
  - Concise record of tests, lint, health, live inference, export, and public
    profile verification.

### Replace

- `docs/demo-script.md`
  - Exact 30-second shot list, narration, caption copy, raw clip names, and
    capture instructions.
- `docs/social-post.md`
  - Final LinkedIn copy with public links, dependency wording, disclosure, and
    hashtags.
- `docs/field-notes.md`
  - Completed report with no promised future metrics or fabricated feedback.
- `docs/submission-checklist.md`
  - Required-first release checklist with optional evaluation work separated.

### Modify

- `pyproject.toml`
  - Add an isolated `demo` dependency group containing `imageio-ffmpeg`.
- `uv.lock`
  - Lock the demo dependency.
- `.gitignore`
  - Ignore generated raw captures, narration audio, graphics, and final video.
- `README.md`
  - Mark submission materials as final and link the public Field Notes report.

### Generated but ignored

- `artifacts/submission/raw/01-hook.mp4`
- `artifacts/submission/raw/02-identify.mp4`
- `artifacts/submission/raw/03-plan.mp4`
- `artifacts/submission/raw/04-calendar.mp4`
- `artifacts/submission/waterleaf-voiceover.txt`
- `artifacts/submission/waterleaf-voiceover.mp3`
- `artifacts/submission/waterleaf-demo.srt`
- `artifacts/submission/waterleaf-end-card.png`
- `artifacts/submission/waterleaf-thumbnail.png`
- `artifacts/submission/waterleaf-demo.mp4`

---

### Task 1: Build Tested Submission Asset Generation

**Files:**
- Create: `scripts/submission_assets.py`
- Create: `tests/test_submission_assets.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add ignored generated-artifact paths**

Append this block to `.gitignore`:

```gitignore
# Generated hackathon submission media
artifacts/submission/
```

- [ ] **Step 2: Write the failing submission-asset tests**

Create `tests/test_submission_assets.py`:

```python
from pathlib import Path

from PIL import Image

from scripts.submission_assets import (
    CAPTION_CUES,
    END_CARD_LINES,
    VOICEOVER,
    generate_voiceover,
    render_srt,
    speech_payload,
    write_static_assets,
)


def test_voiceover_and_srt_match_approved_thirty_second_script():
    assert len(VOICEOVER.split()) == 64
    assert CAPTION_CUES[0][0] == "00:00:00,000"
    assert CAPTION_CUES[-1][1] == "00:00:30,000"
    assert render_srt().endswith("Built with Gradio, llama.cpp, and Modal.\n")
    assert "AI-generated narration" in END_CARD_LINES


def test_speech_payload_uses_approved_model_voice_and_pacing():
    payload = speech_payload()

    assert payload["model"] == "gpt-4o-mini-tts-2025-12-15"
    assert payload["voice"] == "marin"
    assert payload["input"] == VOICEOVER
    assert payload["response_format"] == "mp3"
    assert "27 to 29 seconds" in payload["instructions"]
    assert "Do not add or remove words" in payload["instructions"]


def test_generate_voiceover_writes_api_response(tmp_path):
    class FakeResponse:
        content = b"fake-mp3"

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self):
            self.request = None

        def post(self, url, *, headers, json):
            self.request = (url, headers, json)
            return FakeResponse()

    client = FakeClient()
    destination = tmp_path / "voiceover.mp3"

    generate_voiceover(destination, api_key="test-key", client=client)

    assert destination.read_bytes() == b"fake-mp3"
    assert client.request[0] == "https://api.openai.com/v1/audio/speech"
    assert client.request[1]["Authorization"] == "Bearer test-key"
    assert client.request[2] == speech_payload()


def test_static_assets_use_linkedin_dimensions(tmp_path):
    paths = write_static_assets(tmp_path)

    assert paths["script"].read_text() == VOICEOVER + "\n"
    assert paths["captions"].read_text() == render_srt()
    with Image.open(paths["end_card"]) as image:
        assert image.size == (1920, 1080)
    with Image.open(paths["thumbnail"]) as image:
        assert image.size == (1920, 1080)
```

- [ ] **Step 3: Run the tests and verify that the module is missing**

Run:

```bash
uv run pytest tests/test_submission_assets.py -q
```

Expected: collection fails with
`ModuleNotFoundError: No module named 'scripts.submission_assets'`.

- [ ] **Step 4: Implement the submission asset generator**

Create `scripts/submission_assets.py`:

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Protocol

import httpx
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
BACKGROUND = "#14241a"
PAPER = "#f4f7f2"
LEAF = "#7fc18e"
MUTED = "#bfd0c1"

VOICEOVER = (
    "A garden photo should become something useful. "
    "Waterleaf uses Gemma 4 through llama.cpp to read visible traits, then "
    "grounds its suggestions in GBIF records so you make the final call. "
    "It combines local care baselines with weather rules to create an editable "
    "thirty-day plan. Save the plant, export the calendar, and every reminder "
    "links back to the photo. Built with Gradio, llama.cpp, and Modal."
)

CAPTION_CUES = (
    (
        "00:00:00,000",
        "00:00:04,000",
        ("A garden photo should become something useful.",),
    ),
    (
        "00:00:04,000",
        "00:00:11,000",
        (
            "Waterleaf uses Gemma 4 through llama.cpp",
            "to read visible traits, then grounds its",
            "suggestions in GBIF records...",
        ),
    ),
    (
        "00:00:11,000",
        "00:00:19,000",
        (
            "...so you make the final call. It combines",
            "local care baselines with weather rules to",
            "create an editable thirty-day plan.",
        ),
    ),
    (
        "00:00:19,000",
        "00:00:26,000",
        (
            "Save the plant, export the calendar,",
            "and every reminder links back to the photo.",
        ),
    ),
    (
        "00:00:26,000",
        "00:00:30,000",
        ("Built with Gradio, llama.cpp, and Modal.",),
    ),
)

END_CARD_LINES = (
    "Gemma 4 GGUF  |  llama.cpp  |  Modal  |  Gradio",
    "Backyard AI  |  Llama Champion  |  Field Notes",
    "hf.co/spaces/build-small-hackathon/waterleaf",
    "AI-generated narration",
)


class SpeechClient(Protocol):
    def post(self, url: str, *, headers: dict, json: dict): ...


def render_srt() -> str:
    blocks = []
    for index, (start, end, lines) in enumerate(CAPTION_CUES, start=1):
        blocks.append(
            f"{index}\n{start} --> {end}\n" + "\n".join(lines)
        )
    return "\n\n".join(blocks) + "\n"


def speech_payload() -> dict[str, str]:
    return {
        "model": "gpt-4o-mini-tts-2025-12-15",
        "voice": "marin",
        "input": VOICEOVER,
        "instructions": (
            "Speak in a calm, concise, confident product-demo style. "
            "Target 27 to 29 seconds. Keep a natural pace and make the phrases "
            "'something useful', 'final call', 'thirty-day plan', and "
            "'links back to the photo' easy to hear. Do not add or remove words."
        ),
        "response_format": "mp3",
    }


def generate_voiceover(
    destination: Path,
    *,
    api_key: str,
    client: SpeechClient | None = None,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    owns_client = client is None
    active_client = client or httpx.Client(timeout=120.0)
    try:
        response = active_client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=speech_payload(),
        )
        response.raise_for_status()
        destination.write_bytes(response.content)
    finally:
        if owns_client:
            active_client.close()
    return destination


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        )
        if bold
        else (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
    )
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def _centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    y: int,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((WIDTH - width) / 2, y), text, font=font, fill=fill)


def render_end_card(destination: Path) -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _centered_text(
        draw,
        "Waterleaf",
        y=185,
        font=_font(112, bold=True),
        fill=PAPER,
    )
    _centered_text(
        draw,
        "A garden photo becomes an editable watering calendar.",
        y=335,
        font=_font(42),
        fill=MUTED,
    )
    for index, line in enumerate(END_CARD_LINES):
        _centered_text(
            draw,
            line,
            y=485 + (index * 82),
            font=_font(32, bold=index < 2),
            fill=LEAF if index < 2 else PAPER,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    return destination


def render_thumbnail(destination: Path) -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (120, 120, WIDTH - 120, HEIGHT - 120),
        radius=48,
        fill="#203b29",
        outline=LEAF,
        width=5,
    )
    _centered_text(
        draw,
        "Photo  ->  Watering calendar",
        y=340,
        font=_font(78, bold=True),
        fill=PAPER,
    )
    _centered_text(
        draw,
        "Waterleaf",
        y=520,
        font=_font(64, bold=True),
        fill=LEAF,
    )
    _centered_text(
        draw,
        "Gemma 4 through llama.cpp",
        y=635,
        font=_font(38),
        fill=MUTED,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    return destination


def write_static_assets(output_directory: Path) -> dict[str, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "script": output_directory / "waterleaf-voiceover.txt",
        "captions": output_directory / "waterleaf-demo.srt",
        "end_card": output_directory / "waterleaf-end-card.png",
        "thumbnail": output_directory / "waterleaf-thumbnail.png",
    }
    paths["script"].write_text(VOICEOVER + "\n")
    paths["captions"].write_text(render_srt())
    render_end_card(paths["end_card"])
    render_thumbnail(paths["thumbnail"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Waterleaf hackathon submission assets."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/submission"),
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Call the OpenAI Speech API and write the approved narration.",
    )
    args = parser.parse_args()

    paths = write_static_assets(args.out)
    if args.voice:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY is required for --voice")
        paths["voiceover"] = generate_voiceover(
            args.out / "waterleaf-voiceover.mp3",
            api_key=api_key,
        )

    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the focused tests**

Run:

```bash
uv run pytest tests/test_submission_assets.py -q
```

Expected: `4 passed`.

- [ ] **Step 6: Run Ruff on the new files**

Run:

```bash
uv run ruff check scripts/submission_assets.py tests/test_submission_assets.py
```

Expected: `All checks passed!`

- [ ] **Step 7: Commit the asset generator**

```bash
git add .gitignore scripts/submission_assets.py tests/test_submission_assets.py
git commit -m "feat: generate hackathon submission assets"
```

---

### Task 2: Build Tested Video Composition and Validation

**Files:**
- Create: `scripts/compose_demo.py`
- Create: `tests/test_compose_demo.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Add the isolated demo dependency**

Add this dependency group to `pyproject.toml`:

```toml
demo = [
  "imageio-ffmpeg>=0.6,<1",
]
```

Place it beside the existing `dev` and `deploy` groups.

- [ ] **Step 2: Lock and install the demo dependency**

Run:

```bash
uv sync --group demo
```

Expected: `imageio-ffmpeg` is installed and `uv.lock` changes.

- [ ] **Step 3: Write the failing composition tests**

Create `tests/test_compose_demo.py`:

```python
import pytest

from scripts.compose_demo import (
    MediaProbe,
    compose_command,
    parse_probe,
    validate_demo,
    validate_voiceover,
)


def test_compose_command_uses_approved_timeline_and_codecs(tmp_path):
    command = compose_command(
        ffmpeg="/tmp/ffmpeg",
        raw_directory=tmp_path / "raw",
        assets_directory=tmp_path,
        output=tmp_path / "waterleaf-demo.mp4",
    )
    joined = " ".join(command)

    for name in (
        "01-hook.mp4",
        "02-identify.mp4",
        "03-plan.mp4",
        "04-calendar.mp4",
        "waterleaf-end-card.png",
        "waterleaf-voiceover.mp3",
        "waterleaf-demo.srt",
    ):
        assert name in joined
    assert "concat=n=5:v=1:a=0" in joined
    assert "subtitles=" in joined
    assert "libx264" in command
    assert "aac" in command
    assert command[-1].endswith("waterleaf-demo.mp4")


def test_parse_probe_reads_duration_and_codecs():
    probe = parse_probe(
        """
        Duration: 00:00:30.02, start: 0.000000, bitrate: 1450 kb/s
        Stream #0:0: Video: h264 (High), yuv420p, 1920x1080, 30 fps
        Stream #0:1: Audio: aac (LC), 48000 Hz, stereo
        """
    )

    assert probe == MediaProbe(duration_seconds=30.02, has_h264=True, has_aac=True)


def test_validation_rejects_bad_duration_or_missing_audio():
    validate_demo(MediaProbe(30.0, has_h264=True, has_aac=True))
    validate_voiceover(MediaProbe(28.0, has_h264=False, has_aac=False))

    with pytest.raises(ValueError, match="29.5-30.2"):
        validate_demo(MediaProbe(31.0, has_h264=True, has_aac=True))
    with pytest.raises(ValueError, match="H.264"):
        validate_demo(MediaProbe(30.0, has_h264=False, has_aac=True))
    with pytest.raises(ValueError, match="AAC"):
        validate_demo(MediaProbe(30.0, has_h264=True, has_aac=False))
    with pytest.raises(ValueError, match="24.0-29.5"):
        validate_voiceover(MediaProbe(30.0, has_h264=False, has_aac=True))
```

- [ ] **Step 4: Run the tests and verify that the module is missing**

Run:

```bash
uv run pytest tests/test_compose_demo.py -q
```

Expected: collection fails with
`ModuleNotFoundError: No module named 'scripts.compose_demo'`.

- [ ] **Step 5: Implement the deterministic composer**

Create `scripts/compose_demo.py`:

```python
from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

RAW_CLIPS = (
    ("01-hook.mp4", 4),
    ("02-identify.mp4", 7),
    ("03-plan.mp4", 8),
    ("04-calendar.mp4", 7),
)
END_CARD_SECONDS = 4
OUTPUT_SECONDS = 30


@dataclass(frozen=True)
class MediaProbe:
    duration_seconds: float
    has_h264: bool
    has_aac: bool


def _escaped_subtitle_path(path: Path) -> str:
    return (
        path.as_posix()
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )


def compose_command(
    *,
    ffmpeg: str,
    raw_directory: Path,
    assets_directory: Path,
    output: Path,
) -> list[str]:
    command = [ffmpeg, "-y", "-hide_banner"]
    for name, _ in RAW_CLIPS:
        command.extend(["-i", str(raw_directory / name)])
    command.extend(
        [
            "-loop",
            "1",
            "-t",
            str(END_CARD_SECONDS),
            "-i",
            str(assets_directory / "waterleaf-end-card.png"),
            "-i",
            str(assets_directory / "waterleaf-voiceover.mp3"),
        ]
    )

    filters = []
    durations = [duration for _, duration in RAW_CLIPS] + [END_CARD_SECONDS]
    for index, duration in enumerate(durations):
        filters.append(
            f"[{index}:v]"
            f"trim=duration={duration},"
            "setpts=PTS-STARTPTS,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14241a,"
            "fps=30,format=yuv420p"
            f"[v{index}]"
        )
    inputs = "".join(f"[v{index}]" for index in range(5))
    filters.append(f"{inputs}concat=n=5:v=1:a=0[base]")
    subtitle_path = _escaped_subtitle_path(
        assets_directory / "waterleaf-demo.srt"
    )
    filters.append(
        "[base]"
        f"subtitles='{subtitle_path}':"
        "force_style='FontName=Arial,FontSize=30,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=3,Shadow=0,MarginV=55,Alignment=2'"
        "[video]"
    )

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[video]",
            "-map",
            "5:a:0",
            "-t",
            str(OUTPUT_SECONDS),
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def parse_probe(output: str) -> MediaProbe:
    match = re.search(
        r"Duration: (\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)",
        output,
    )
    if not match:
        raise ValueError("FFmpeg output did not contain a duration")
    hours, minutes, seconds = match.groups()
    duration = (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
    return MediaProbe(
        duration_seconds=duration,
        has_h264="Video: h264" in output,
        has_aac="Audio: aac" in output,
    )


def probe_media(ffmpeg: str, path: Path) -> MediaProbe:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return parse_probe(result.stderr)


def validate_voiceover(probe: MediaProbe) -> None:
    if not 24.0 <= probe.duration_seconds <= 29.5:
        raise ValueError(
            "Voiceover duration must be 24.0-29.5 seconds; "
            f"got {probe.duration_seconds:.2f}"
        )


def validate_demo(probe: MediaProbe) -> None:
    if not 29.5 <= probe.duration_seconds <= 30.2:
        raise ValueError(
            "Demo duration must be 29.5-30.2 seconds; "
            f"got {probe.duration_seconds:.2f}"
        )
    if not probe.has_h264:
        raise ValueError("Demo must contain H.264 video")
    if not probe.has_aac:
        raise ValueError("Demo must contain AAC audio")


def locate_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compose and validate the Waterleaf LinkedIn demo."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("artifacts/submission/raw"),
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("artifacts/submission"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/submission/waterleaf-demo.mp4"),
    )
    args = parser.parse_args()

    ffmpeg = locate_ffmpeg()
    required = [args.raw_dir / name for name, _ in RAW_CLIPS]
    required.extend(
        [
            args.assets_dir / "waterleaf-end-card.png",
            args.assets_dir / "waterleaf-voiceover.mp3",
            args.assets_dir / "waterleaf-demo.srt",
        ]
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing submission inputs:\n" + "\n".join(missing))

    validate_voiceover(
        probe_media(ffmpeg, args.assets_dir / "waterleaf-voiceover.mp3")
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        compose_command(
            ffmpeg=ffmpeg,
            raw_directory=args.raw_dir,
            assets_directory=args.assets_dir,
            output=args.output,
        ),
        check=True,
    )
    probe = probe_media(ffmpeg, args.output)
    validate_demo(probe)
    print(
        f"validated: {args.output} "
        f"({probe.duration_seconds:.2f}s, H.264, AAC)"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run focused tests and lint**

Run:

```bash
uv run pytest tests/test_compose_demo.py -q
uv run ruff check scripts/compose_demo.py tests/test_compose_demo.py
```

Expected:

```text
3 passed
All checks passed!
```

- [ ] **Step 7: Verify the bundled FFmpeg binary**

Run:

```bash
FFMPEG=$(uv run --group demo python -c \
  "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FFMPEG" -hide_banner -filters | rg ' subtitles '
"$FFMPEG" -version | sed -n '1p'
```

Expected: the `subtitles` filter is listed and a non-empty FFmpeg version
string prints.

- [ ] **Step 8: Commit the composer**

```bash
git add pyproject.toml uv.lock scripts/compose_demo.py tests/test_compose_demo.py
git commit -m "feat: compose and validate demo video"
```

---

### Task 3: Replace Draft Publication Copy

**Files:**
- Modify: `docs/demo-script.md`
- Modify: `docs/social-post.md`
- Modify: `docs/field-notes.md`
- Modify: `docs/submission-checklist.md`
- Modify: `README.md`

- [ ] **Step 1: Replace the demo script**

Replace `docs/demo-script.md` with:

```markdown
# Waterleaf 30-Second Demo Script

## Output

- LinkedIn native video
- 1920x1080, 16:9, 30 fps
- MP4 with H.264 video and AAC audio
- Maximum duration: 30 seconds
- Burned-in captions plus `waterleaf-demo.srt`
- AI-generated narration disclosed on the end card and in the LinkedIn post

## Raw Clips

Record clean clips without notifications, browser chrome changes, or visible
secrets. Each source clip may be longer than its final duration because the
composition script trims it.

1. `artifacts/submission/raw/01-hook.mp4`
   - Final duration: 4 seconds
   - Show the public plant profile with the lavender image and upcoming dates.
2. `artifacts/submission/raw/02-identify.mp4`
   - Final duration: 7 seconds
   - Show the licensed lavender image in Waterleaf.
   - Cut directly to visible traits and the three GBIF-backed matches.
3. `artifacts/submission/raw/03-plan.mp4`
   - Final duration: 8 seconds
   - Confirm English lavender.
   - Reveal editable 30-day dates and the reason/confidence columns.
4. `artifacts/submission/raw/04-calendar.mp4`
   - Final duration: 7 seconds
   - Show the saved plant card, generated ICS, and linked public plant
     profile.

The final four seconds use the generated
`artifacts/submission/waterleaf-end-card.png`.

## Timed Story

### 0-4 seconds

Visual: public plant profile with source image and upcoming dates.

Caption: `Turn a garden photo into a watering plan.`

Voice: `A garden photo should become something useful.`

### 4-11 seconds

Visual: licensed photo, visible traits, and grounded species matches.

Voice: `Waterleaf uses Gemma 4 through llama.cpp to read visible traits, then
grounds its suggestions in GBIF records...`

### 11-19 seconds

Visual: select English lavender and reveal editable watering dates.

Caption: `The model suggests. You confirm.`

Voice: `...so you make the final call. It combines local care baselines with
weather rules to create an editable thirty-day plan.`

### 19-26 seconds

Visual: saved plant card, generated ICS, and public plant profile.

Voice: `Save the plant, export the calendar, and every reminder links back to
the photo.`

### 26-30 seconds

Visual: Waterleaf end card with stack, claimed categories, Space URL, and
`AI-generated narration`.

Voice: `Built with Gradio, llama.cpp, and Modal.`

## Full Voiceover

A garden photo should become something useful. Waterleaf uses Gemma 4 through
llama.cpp to read visible traits, then grounds its suggestions in GBIF records
so you make the final call. It combines local care baselines with weather rules
to create an editable thirty-day plan. Save the plant, export the calendar, and
every reminder links back to the photo. Built with Gradio, llama.cpp, and Modal.

## Editing Rules

- Show the outcome before the setup.
- Keep only decisive interactions; remove loading and typing delays.
- Do not show login, deletion, or a dashboard tour.
- Do not claim Off the Grid, fully local operation, identification accuracy, or
  user validation.
- The video must remain understandable when muted.
```

- [ ] **Step 2: Replace the LinkedIn post draft**

Replace `docs/social-post.md` with:

```markdown
# LinkedIn Post

I built Waterleaf: a garden photo becomes an editable watering calendar.

Upload 1-3 photos, review the visible traits, and confirm a GBIF-backed species
match. Waterleaf combines a local care baseline with transparent weather rules
to produce editable 30-day watering dates, then exports one calendar for the
garden. Every reminder links back to the plant photo.

Under the hood, Gemma 4 26B-A4B runs as a GGUF through llama.cpp on Modal. The
model is constrained to structured visual observations and reranking valid
taxonomy records; deterministic code creates the watering schedule. Taxonomy
and forecast data come from GBIF and Open-Meteo.

Try Waterleaf:
https://huggingface.co/spaces/build-small-hackathon/waterleaf

Field Notes:
https://huggingface.co/spaces/build-small-hackathon/waterleaf/blob/main/docs/field-notes.md

Code:
https://github.com/hkaraoguz/waterleaf

AI-generated narration created with OpenAI text-to-speech.

Demo image: "Lavender plants growing in a garden" by Brooke Balentine,
Unsplash License.

#BuildSmall #HuggingFace #Gradio #llamacpp #Modal #Gemma
```

- [ ] **Step 3: Replace the Field Notes report**

Replace `docs/field-notes.md` with:

```markdown
# Field Notes: Turning a Garden Photo into a Watering Calendar

Waterleaf began with a narrow question: after a model identifies a garden
plant, what useful thing should happen next?

A species name is interesting for a moment. A watering reminder can change
what happens in the garden. I built Waterleaf to turn one to three outdoor
plant photographs into a grounded species choice, an editable 30-day watering
plan, and one portable calendar for the whole garden.

This was a product hypothesis, not a completed user study. No gardener quote or
formal usability result is claimed here.

## Identification is not the final artifact

The first design decision was to keep the language model away from final
authority.

Gemma 4 receives the photographs and returns only visible observations:

- botanical traits such as leaf shape, flower form, and growth habit;
- up to five proposed names;
- visible planting context, limited to container versus in-ground;
- a rough visible size.

Those names are provisional. Waterleaf resolves them through the GBIF Species
API and keeps valid plant species records. Gemma then reranks only those
records. Unknown keys are discarded, and the gardener confirms or replaces the
species before continuing.

This division of labor matters. The model is useful at seeing and comparing.
GBIF is the taxonomy source. The person remains the decision-maker.

## Running Gemma 4 through llama.cpp

The vision model is `google/gemma-4-26B-A4B-it`, served from the
`ggml-org/gemma-4-26B-A4B-it-GGUF` repository as a Q4_K_M GGUF. Gemma 4 is a
mixture-of-experts model with roughly 4B active parameters per token, while the
total model remains below the hackathon's 32B limit.

The runtime is a pinned llama.cpp CUDA server on a Modal L4:

- llama.cpp image `server-cuda13-b9445`;
- 8K context;
- full GPU offload;
- Flash Attention;
- Q8 key and value caches;
- one parallel request slot;
- automatic multimodal projector retrieval.

The first visual pass disables thinking and uses a strict JSON schema. The
candidate reranking pass enables a bounded 256-token thinking budget and still
requires a strict final JSON response. The application rejects ranking keys
that were not produced by GBIF.

The Hugging Face Space remains a small Gradio and FastAPI application. It calls
the protected Modal endpoint using proxy-auth headers.

## Scheduling without pretending the model knows the weather

The language model never chooses watering dates.

Waterleaf starts with a small local care-baseline catalog. When a selected
species has no baseline, the user must enter an interval explicitly. The
scheduler then:

1. averages the minimum and maximum care interval;
2. shortens the interval for container plants;
3. defers a near-term event after meaningful forecast rain;
4. advances a near-term event during hot or drying conditions;
5. labels dates beyond the 16-day forecast as seasonal estimates.

Every date is visible before saving. The user can edit or remove any row. If
the forecast API fails, Waterleaf still produces a seasonal schedule instead
of failing the workflow.

This deterministic layer is easier to inspect, test, and correct than asking a
language model to invent a care calendar.

## The calendar is the product

Waterleaf exports one RFC 5545-compatible ICS file containing 15-minute events
for all saved plants.

Each event includes:

- a stable UID;
- the preferred local watering time;
- a 30-minute alarm;
- the species and scheduling reason;
- a public plant-profile URL;
- an image attachment URL.

Calendar clients differ in how they display remote attachments. The public
profile is the portable fallback: it shows the plant image, species, planting
context, care cadence, and upcoming dates without exposing the owner or stored
location.

## Privacy boundaries

Uploaded images are resized, converted to JPEG, and rewritten without EXIF.
Coordinates are rounded before storage. Account identity and location are not
present on public plant pages. Public profiles use long opaque slugs, but they
are intentionally public because calendar clients need to open them.

That last point is a limitation, not a security guarantee. Anyone with a public
profile URL can view that plant page.

## Evidence

At submission time:

- the public Space and `/health` endpoint returned HTTP 200;
- the complete automated suite contained 47 passing tests;
- Ruff reported no issues;
- tests covered constrained multimodal requests, grounded reranking,
  deterministic scheduling, forecast fallback, image normalization, owner
  isolation, public privacy boundaries, ICS generation, and submission assets;
- the deployed guest flow was captured through identify, confirm, and preview;
- save, export, and public-profile footage was captured from the same
  application code with isolated local data.

I did not complete a real labeled identification benchmark before the required
submission assets. I therefore do not publish an accuracy number. I also do not
claim the Off the Grid badge: model inference runs on Modal, while taxonomy,
geocoding, and forecast data use GBIF and Open-Meteo.

## Failure modes and limitations

- A photograph can be visually ambiguous, especially without flowers or useful
  scale.
- The top match can be wrong; confirmation is required.
- Taxonomy search requires GBIF.
- Location and forecast enrichment require Open-Meteo.
- Only a small set of species and genera have bundled care baselines.
- Unknown plants require a manual interval.
- Forecast adjustments cover 16 days; later dates are seasonal estimates.
- Calendar clients handle image attachments inconsistently.
- Public profile links are intentionally shareable.
- Watering suggestions are not horticultural guarantees.

## What I learned

The strongest model behavior came from reducing its authority:

1. ask for visible observations rather than certainty;
2. resolve names in a real taxonomy;
3. rerank only valid records;
4. make the human choice explicit;
5. keep the schedule deterministic and editable.

The same restraint improved the demo. The interesting story is not a form or a
model response. It is the transformation from a photograph to an artifact that
appears in an existing daily tool.

## Links

- Space: <https://huggingface.co/spaces/build-small-hackathon/waterleaf>
- Source: <https://github.com/hkaraoguz/waterleaf>
- Architecture: [architecture.md](architecture.md)
- Demo script: [demo-script.md](demo-script.md)

## Demo image attribution

"Lavender plants growing in a garden" by Brooke Balentine, used under the
Unsplash License:
<https://unsplash.com/photos/lavender-plants-growing-in-a-garden-o-8pxOIAJcg>
```

- [ ] **Step 4: Replace the submission checklist**

Replace `docs/submission-checklist.md` with:

```markdown
# Submission Checklist

## Required

- [x] Deploy the protected Modal llama.cpp service.
- [x] Create and mount the Hugging Face Storage Bucket at `/data`.
- [x] Deploy `build-small-hackathon/waterleaf`.
- [x] Verify the Space root and `/health` endpoint return HTTP 200.
- [x] Approve the outcome-first 30-second demo design.
- [x] Approve the LinkedIn post and Field Notes positioning.
- [ ] Add the licensed lavender image and attribution.
- [ ] Run the complete test suite and Ruff.
- [ ] Capture one live end-to-end identification, save, export, and profile flow.
- [ ] Generate the AI narration, captions, end card, and thumbnail.
- [ ] Assemble and validate the 30-second MP4.
- [ ] Watch the video muted and with audio at desktop and mobile sizes.
- [ ] Upload the final repository to the Hugging Face Space.
- [ ] Verify the public Field Notes link in a signed-out session.
- [ ] Publish the native LinkedIn video and post.
- [ ] Verify the LinkedIn post, Space, Field Notes, source, and profile links.
- [ ] Submit the Space and LinkedIn post URLs before June 15, 2026.

## Optional After Required Assets Are Public

- [ ] Run at least 20 consented real-garden evaluation cases.
- [ ] Record repeatable warm and cold inference latency.
- [ ] Test one-, two-, and three-photo identification cases.
- [ ] Import the ICS into additional calendar clients.
- [ ] Collect genuine gardener feedback for a later update.

## Claims

- Claim: Backyard AI.
- Claim: Llama Champion.
- Claim: Modal-powered.
- Claim: Field Notes.
- Do not claim: Off the Grid.
- Do not claim: measured accuracy, measured latency, or user validation unless
  the corresponding evidence is completed and published.
```

- [ ] **Step 5: Mark submission materials as final in README**

Replace `README.md:265-274` with:

```markdown
## Submission Materials

- [Field Notes](docs/field-notes.md)
- [30-second demo script](docs/demo-script.md)
- [LinkedIn post](docs/social-post.md)
- [Submission evidence](docs/submission-evidence.md)
- [Submission checklist](docs/submission-checklist.md)

Target quests: Backyard AI, Llama Champion, Modal-powered, and Field Notes.
Waterleaf does not claim Off the Grid because inference, taxonomy, and weather
data use cloud-hosted services.
```

- [ ] **Step 6: Check the copy for forbidden placeholders and claims**

Run:

```bash
rg -n \
  'ADD ARTICLE|TBD|TODO|60-90|known gardener|will include|Off the Grid badge|fully offline' \
  docs README.md
```

Expected: no placeholder or old-demo matches. The only permitted Off the Grid
matches explicitly say that Waterleaf does not claim it.

- [ ] **Step 7: Run Markdown-adjacent repository checks**

Run:

```bash
git diff --check
uv run pytest -q
uv run ruff check .
```

Expected:

```text
47 passed
All checks passed!
```

- [ ] **Step 8: Commit the final publication copy**

```bash
git add README.md docs/demo-script.md docs/social-post.md docs/field-notes.md \
  docs/submission-checklist.md
git commit -m "docs: finalize hackathon submission copy"
```

---

### Task 4: Add Licensed Input and Lock Evidence

**Files:**
- Create: `assets/demo/lavender-garden-brooke-balentine.jpg`
- Create: `assets/demo/ATTRIBUTION.md`
- Create: `docs/submission-evidence.md`

- [ ] **Step 1: Download the licensed Unsplash image**

Run:

```bash
mkdir -p assets/demo
curl -L --fail \
  'https://images.unsplash.com/photo-1746933240463-c2d317a4c1a0?q=90&w=1920&auto=format&fit=crop' \
  -o assets/demo/lavender-garden-brooke-balentine.jpg
```

Expected: curl exits zero.

- [ ] **Step 2: Verify the image**

Run:

```bash
file assets/demo/lavender-garden-brooke-balentine.jpg
uv run python -c \
  "from PIL import Image; p='assets/demo/lavender-garden-brooke-balentine.jpg'; \
im=Image.open(p); print(im.format, im.size); assert im.format == 'JPEG'; \
assert im.width >= 1200 and im.height >= 600"
```

Expected: a JPEG at least 1200 pixels wide and 600 pixels high.

- [ ] **Step 3: Record the attribution**

Create `assets/demo/ATTRIBUTION.md`:

```markdown
# Demo Asset Attribution

## Lavender garden photograph

- Title: "Lavender plants growing in a garden."
- Photographer: Brooke Balentine
- Source: https://unsplash.com/photos/lavender-plants-growing-in-a-garden-o-8pxOIAJcg
- License: Unsplash License
- Local file: `lavender-garden-brooke-balentine.jpg`
- Use: licensed sample input and demo-video visual

This image is a licensed sample. It is not user-submitted research data and
does not represent a Waterleaf usability study.
```

- [ ] **Step 4: Run the full technical baseline**

Run:

```bash
uv run pytest -q
uv run ruff check .
curl --fail https://build-small-hackathon-waterleaf.hf.space/health
```

Expected:

```text
47 passed
All checks passed!
{"status":"ok"}
```

- [ ] **Step 5: Verify one live end-to-end flow**

Open:

```text
https://build-small-hackathon-waterleaf.hf.space/
```

Perform these exact checks:

1. Sign in with Hugging Face.
2. Upload `assets/demo/lavender-garden-brooke-balentine.jpg`.
3. Run analysis and confirm that visible traits and database-backed candidates
   appear.
4. Select the best valid species record.
5. Preview the Stockholm schedule.
6. Save the plant.
7. Generate the 30-day calendar.
8. Open the public plant profile from the garden card.
9. Open the public image.
10. Download the ICS and inspect one event.

Stop and repair the product before continuing if any required step fails.

- [ ] **Step 6: Create the evidence record after the checks pass**

Create `docs/submission-evidence.md`:

```markdown
# Waterleaf Submission Evidence

Verified on June 14, 2026.

## Automated checks

- `uv run pytest -q`: 47 passed.
- `uv run ruff check .`: all checks passed.

## Deployment

- Space: https://huggingface.co/spaces/build-small-hackathon/waterleaf
- Direct app: https://build-small-hackathon-waterleaf.hf.space/
- Health: `GET /health` returned HTTP 200 and `{"status":"ok"}`.

## Live workflow

A signed-in live run completed:

1. licensed lavender photo upload;
2. Gemma 4 visual analysis through llama.cpp;
3. GBIF-backed candidate confirmation;
4. editable weather-aware schedule preview;
5. plant save;
6. whole-garden ICS generation;
7. public plant profile and image access.

## Claim boundaries

- Waterleaf claims Llama Champion because the model runs through llama.cpp.
- Waterleaf is Modal-powered.
- Waterleaf does not claim Off the Grid.
- No identification accuracy, repeatable latency, or gardener-validation metric
  is claimed in the submission.
```

- [ ] **Step 7: Commit licensed input and evidence**

```bash
git add assets/demo/lavender-garden-brooke-balentine.jpg \
  assets/demo/ATTRIBUTION.md docs/submission-evidence.md
git commit -m "docs: add demo attribution and submission evidence"
```

---

### Task 5: Capture the Four Live Product Clips

**Files:**
- Generate: `artifacts/submission/raw/01-hook.mp4`
- Generate: `artifacts/submission/raw/02-identify.mp4`
- Generate: `artifacts/submission/raw/03-plan.mp4`
- Generate: `artifacts/submission/raw/04-calendar.mp4`

- [ ] **Step 1: Generate static production assets before recording**

Run:

```bash
uv run python scripts/submission_assets.py --out artifacts/submission
mkdir -p artifacts/submission/raw
```

Expected output lists the script, captions, end card, and thumbnail paths.

- [ ] **Step 2: Prepare the live recording state**

Use the direct Space URL:

```text
https://build-small-hackathon-waterleaf.hf.space/
```

Before recording:

1. Set the browser window to a clean 16:9 layout.
2. Close unrelated tabs and hide bookmarks containing private data.
3. Disable notifications.
4. Keep the cursor still unless it demonstrates a click.
5. Use the licensed lavender image.
6. Pre-warm the model with one analysis run.
7. Pre-populate the form values needed for the schedule.
8. Keep all secrets, Modal settings, and account menus off screen.

- [ ] **Step 3: Record `01-hook.mp4`**

Record the public plant profile with the lavender visual and upcoming watering
dates for at least five seconds.
Save it as:

```text
artifacts/submission/raw/01-hook.mp4
```

The visible reminder must include the plant identity or image context.

- [ ] **Step 4: Record `02-identify.mp4`**

Record the Waterleaf Add Plant flow from the licensed image to visible traits
and candidate results. Waiting time may remain in the raw file because the
final edit cuts directly to the result. Save it as:

```text
artifacts/submission/raw/02-identify.mp4
```

- [ ] **Step 5: Record `03-plan.mp4`**

Record selecting English lavender and revealing the editable 30-day watering
dates. Keep the date, reason, and confidence columns legible. Save it as:

```text
artifacts/submission/raw/03-plan.mp4
```

- [ ] **Step 6: Record `04-calendar.mp4`**

Record saving the plant, generating the calendar, showing the event, and
opening the public profile. Save it as:

```text
artifacts/submission/raw/04-calendar.mp4
```

- [ ] **Step 7: Verify all raw files are readable**

Run:

```bash
uv run --group demo python -c '
from pathlib import Path
import imageio_ffmpeg
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
from scripts.compose_demo import RAW_CLIPS, probe_media
for name, minimum in RAW_CLIPS:
    path = Path("artifacts/submission/raw") / name
    probe = probe_media(ffmpeg, path)
    print(name, probe.duration_seconds)
    assert probe.duration_seconds >= minimum
'
```

Expected: all four names print with durations at least 4, 7, 8, and 7 seconds.

---

### Task 6: Generate Narration, Compose, and QA the Video

**Files:**
- Generate: `artifacts/submission/waterleaf-voiceover.mp3`
- Generate: `artifacts/submission/waterleaf-demo.mp4`

- [ ] **Step 1: Generate the approved AI voiceover**

Run:

```bash
set -a
source .env.local
set +a
uv run python scripts/submission_assets.py \
  --out artifacts/submission \
  --voice
```

Expected: `artifacts/submission/waterleaf-voiceover.mp3` is created without
printing the API key.

- [ ] **Step 2: Check narration duration before composition**

Run:

```bash
uv run --group demo python -c '
from pathlib import Path
import imageio_ffmpeg
from scripts.compose_demo import probe_media, validate_voiceover
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
probe = probe_media(ffmpeg, Path("artifacts/submission/waterleaf-voiceover.mp3"))
validate_voiceover(probe)
print(f"voiceover_seconds={probe.duration_seconds:.2f}")
'
```

Expected: duration is between 24.0 and 29.5 seconds.

If it is outside that range, adjust only the pacing sentence in
`speech_payload()["instructions"]`, update the corresponding assertion, rerun
the focused test, and regenerate the narration. Do not change the approved
64-word script without user approval.

- [ ] **Step 3: Compose and validate the final MP4**

Run:

```bash
uv run --group demo python scripts/compose_demo.py \
  --raw-dir artifacts/submission/raw \
  --assets-dir artifacts/submission \
  --output artifacts/submission/waterleaf-demo.mp4
```

Expected:

```text
validated: artifacts/submission/waterleaf-demo.mp4 (29.5-30.2s, H.264, AAC)
```

- [ ] **Step 4: Perform muted visual QA**

Watch `artifacts/submission/waterleaf-demo.mp4` muted and verify:

1. the first frame communicates photo-to-calendar;
2. the real app is visible for the identification and plan beats;
3. every caption is readable before it changes;
4. the species confirmation is visible;
5. the calendar/profile payoff is visible;
6. the end card remains on screen for four seconds;
7. `AI-generated narration` is visible;
8. no secret, private account detail, or notification appears.

- [ ] **Step 5: Perform audio QA**

Watch with audio and verify:

1. speech is calm and not rushed;
2. speech is synchronized with the five visual beats;
3. no final words are truncated;
4. there is no long silence at the start;
5. the final phrase lands during the end card.

- [ ] **Step 6: Perform mobile-size QA**

View the video at approximately 390 pixels wide. Verify that captions, the
species choice, schedule table, Space name, and disclosure remain legible.

If a QA check fails, update the raw clip, caption wording, or card rendering;
rerun the focused tests and composition command; repeat all three QA passes.

- [ ] **Step 7: Run final repository verification**

Run:

```bash
git diff --check
uv run pytest -q
uv run ruff check .
git status --short
```

Expected:

```text
47 passed
All checks passed!
```

Only intended tracked source and documentation files may appear in
`git status`; generated media remains ignored.

---

### Task 7: Publish, Verify Public Links, and Submit

**Files:**
- Modify: `docs/submission-checklist.md`
- Modify only if facts changed: `docs/submission-evidence.md`

- [ ] **Step 1: Upload the final tracked repository to the Space**

Run:

```bash
hf upload build-small-hackathon/waterleaf . . \
  --repo-type space \
  --exclude '.git/**' \
  --exclude '.venv/**' \
  --exclude '.pytest_cache/**' \
  --exclude '.ruff_cache/**' \
  --exclude '.superpowers/**' \
  --exclude '**/__pycache__/**' \
  --exclude '*.pyc' \
  --exclude 'data/**' \
  --exclude 'artifacts/**' \
  --exclude '.env' \
  --exclude '.env.*'
```

Expected: upload succeeds without transmitting `.env.local` or generated raw
media.

- [ ] **Step 2: Verify the public report and application signed out**

Open these exact URLs in a signed-out browser:

```text
https://huggingface.co/spaces/build-small-hackathon/waterleaf
https://build-small-hackathon-waterleaf.hf.space/health
https://huggingface.co/spaces/build-small-hackathon/waterleaf/blob/main/docs/field-notes.md
https://github.com/hkaraoguz/waterleaf
```

Expected:

- the Space loads;
- health returns `{"status":"ok"}`;
- Field Notes render publicly;
- the source repository loads publicly.

- [ ] **Step 3: Publish the LinkedIn native video**

This is an external side effect and must be performed or explicitly confirmed
by the user.

Upload:

```text
artifacts/submission/waterleaf-demo.mp4
```

Also upload:

```text
artifacts/submission/waterleaf-thumbnail.png
artifacts/submission/waterleaf-demo.srt
```

Paste the exact contents of `docs/social-post.md`. Confirm:

- visibility is public;
- the native video preview works;
- the thumbnail is selected;
- captions are enabled;
- the post contains the AI-generated narration disclosure;
- the post contains the licensed-image attribution;
- all three public links are clickable.

- [ ] **Step 4: Verify the published LinkedIn post**

Open the published post in a signed-out/private browser and check:

1. video playback starts;
2. captions appear;
3. the video is 30 seconds or less;
4. the Space link opens;
5. the Field Notes link opens;
6. the GitHub link opens;
7. the post does not claim Off the Grid, accuracy, latency, or user validation.

- [ ] **Step 5: Complete the required checklist**

Mark only verified required items complete in `docs/submission-checklist.md`.
Leave optional work unchecked unless it was actually completed.

- [ ] **Step 6: Commit release documentation**

```bash
git add docs/submission-checklist.md docs/submission-evidence.md
git commit -m "docs: record hackathon submission verification"
```

- [ ] **Step 7: Push the final commit and refresh the Space repository**

Run:

```bash
git push origin feat/waterleaf
hf upload build-small-hackathon/waterleaf . . \
  --repo-type space \
  --exclude '.git/**' \
  --exclude '.venv/**' \
  --exclude '.pytest_cache/**' \
  --exclude '.ruff_cache/**' \
  --exclude '.superpowers/**' \
  --exclude '**/__pycache__/**' \
  --exclude '*.pyc' \
  --exclude 'data/**' \
  --exclude 'artifacts/**' \
  --exclude '.env' \
  --exclude '.env.*'
```

Expected: the GitHub push and final Space upload succeed without transmitting
secrets or generated raw media.

- [ ] **Step 8: Submit the hackathon entry**

Submit:

- Space:
  `https://huggingface.co/spaces/build-small-hackathon/waterleaf`
- Social/demo:
  the verified public LinkedIn post URL
- Field Notes:
  `https://huggingface.co/spaces/build-small-hackathon/waterleaf/blob/main/docs/field-notes.md`

Claim:

- Backyard AI
- Llama Champion
- Modal-powered
- Field Notes

Do not claim:

- Off the Grid
- measured accuracy
- measured latency
- user validation

---

## Final Stop Conditions

Do not call the submission complete until all of these are true:

- the public Space is healthy;
- the public Field Notes report renders;
- the LinkedIn post is public;
- the native video plays and is at most 30 seconds;
- captions and AI-voice disclosure are present;
- the sample image attribution is present;
- all required public links work signed out;
- 47 tests pass and Ruff is clean;
- the checklist reflects only completed facts;
- the hackathon form contains the verified Space, LinkedIn, and Field Notes URLs.
