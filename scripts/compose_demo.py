from __future__ import annotations

import argparse
import re
import subprocess
import sys
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


def _normalized_video_filter(index: int, duration: int) -> str:
    return (
        f"[{index}:v]"
        f"tpad=stop_mode=clone:stop_duration={duration},"
        f"trim=duration={duration},"
        "setpts=PTS-STARTPTS,"
        "setsar=1,"
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14241a,"
        "fps=30,format=yuv420p"
        f"[v{index}]"
    )


def _escape_subtitle_filename(path: Path) -> str:
    escaped = []
    for character in str(path):
        if character == "\\":
            escaped.append("\\\\" * 2)
        elif character == ":":
            escaped.append("\\\\" + ":")
        elif character == "'":
            escaped.append("\\\\" + "\\'")
        elif character in ",;[]":
            escaped.append("\\" + character)
        else:
            escaped.append(character)
    return "".join(escaped)


def _subtitle_filter(path: Path) -> str:
    return (
        "subtitles=filename="
        f"{_escape_subtitle_filename(path)}:"
        "force_style='FontName=Arial\\,FontSize=30\\,"
        "PrimaryColour=&H00FFFFFF\\,OutlineColour=&H00000000\\,"
        "BorderStyle=1\\,Outline=3\\,Shadow=0\\,MarginV=55\\,Alignment=2'"
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
        filters.append(_normalized_video_filter(index, duration))

    filters.append("".join(f"[v{index}]" for index in range(5)) + "concat=n=5:v=1:a=0[base]")
    filters.append(f"[base]{_subtitle_filter(assets_directory / 'waterleaf-demo.srt')}[video]")

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


def _probe_error_tail(text: str, *, max_lines: int = 3, max_chars: int = 240) -> str:
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        return "no stderr output"
    tail = " | ".join(non_empty_lines[-max_lines:])
    if len(tail) <= max_chars:
        return tail
    return "..." + tail[-(max_chars - 3) :]


def parse_probe(text: str) -> MediaProbe:
    match = re.search(
        r"duration\s*:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError(
            "FFmpeg output did not contain a duration. "
            f"Last output: {_probe_error_tail(text)}"
        )

    hours, minutes, seconds = match.groups()
    duration_seconds = (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
    lower_text = text.lower()
    return MediaProbe(
        duration_seconds=duration_seconds,
        has_h264=bool(re.search(r"video:\s*h264\b", lower_text)),
        has_aac=bool(re.search(r"audio:\s*aac\b", lower_text)),
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


def _required_inputs(raw_directory: Path, assets_directory: Path) -> list[Path]:
    return [raw_directory / name for name, _ in RAW_CLIPS] + [
        assets_directory / "waterleaf-end-card.png",
        assets_directory / "waterleaf-voiceover.mp3",
        assets_directory / "waterleaf-demo.srt",
    ]


def _temporary_output_path(output: Path) -> Path:
    return output.with_suffix(".tmp" + output.suffix)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compose and validate the Waterleaf LinkedIn demo."
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("artifacts/submission/raw"))
    parser.add_argument("--assets-dir", type=Path, default=Path("artifacts/submission"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/submission/waterleaf-demo.mp4"),
    )
    args = parser.parse_args()

    missing = [
        path
        for path in _required_inputs(args.raw_dir, args.assets_dir)
        if not path.is_file()
    ]
    if missing:
        print("Missing submission inputs:", file=sys.stderr)
        for path in missing:
            print(path, file=sys.stderr)
        raise SystemExit(1)

    ffmpeg = locate_ffmpeg()
    validate_voiceover(probe_media(ffmpeg, args.assets_dir / "waterleaf-voiceover.mp3"))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = _temporary_output_path(args.output)
    if temporary_output.exists():
        temporary_output.unlink()

    try:
        subprocess.run(
            compose_command(
                ffmpeg=ffmpeg,
                raw_directory=args.raw_dir,
                assets_directory=args.assets_dir,
                output=temporary_output,
            ),
            check=True,
        )

        probe = probe_media(ffmpeg, temporary_output)
        validate_demo(probe)
        temporary_output.replace(args.output)
    except Exception:
        if temporary_output.exists():
            temporary_output.unlink()
        raise

    print(f"validated: {args.output} ({probe.duration_seconds:.2f}s, H.264, AAC)")


if __name__ == "__main__":
    main()
