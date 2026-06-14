from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.compose_demo import (
    END_CARD_SECONDS,
    OUTPUT_SECONDS,
    RAW_CLIPS,
    MediaProbe,
    _subtitle_filter,
    compose_command,
    main,
    parse_probe,
    validate_demo,
    validate_voiceover,
)


def _filter_complex(command: list[str]) -> str:
    return command[command.index("-filter_complex") + 1]


def test_compose_command_uses_approved_timeline_and_codecs(tmp_path: Path):
    raw_directory = tmp_path / "raw"
    assets_directory = tmp_path / "assets"
    output = tmp_path / "out" / "waterleaf-demo.mp4"

    command = compose_command(
        ffmpeg="/tmp/ffmpeg",
        raw_directory=raw_directory,
        assets_directory=assets_directory,
        output=output,
    )
    joined = " ".join(command)
    filter_complex = _filter_complex(command)

    assert command[:3] == ["/tmp/ffmpeg", "-y", "-hide_banner"]
    assert command[3:11] == [
        "-i",
        str(raw_directory / "01-hook.mp4"),
        "-i",
        str(raw_directory / "02-identify.mp4"),
        "-i",
        str(raw_directory / "03-plan.mp4"),
        "-i",
        str(raw_directory / "04-calendar.mp4"),
    ]
    assert command[11:17] == [
        "-loop",
        "1",
        "-t",
        str(END_CARD_SECONDS),
        "-i",
        str(assets_directory / "waterleaf-end-card.png"),
    ]
    assert command[17:19] == ["-i", str(assets_directory / "waterleaf-voiceover.mp3")]

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

    for index, duration in enumerate((4, 7, 8, 7, 4)):
        assert (
            f"[{index}:v]trim=duration={duration},"
            "setpts=PTS-STARTPTS,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14241a,"
            "fps=30,format=yuv420p"
            f"[v{index}]"
        ) in filter_complex

    assert "[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0[base]" in filter_complex
    assert "subtitles=filename=" in filter_complex
    assert "force_style='FontName=Arial\\,FontSize=30\\," in filter_complex
    assert "Outline=3\\,Shadow=0\\,MarginV=55\\,Alignment=2'" in filter_complex
    assert command[command.index("-map") : command.index("-map") + 4] == [
        "-map",
        "[video]",
        "-map",
        "5:a:0",
    ]
    output_t_index = max(index for index, value in enumerate(command) if value == "-t")
    output_r_index = max(index for index, value in enumerate(command) if value == "-r")
    assert command[output_t_index : output_t_index + 2] == ["-t", str(OUTPUT_SECONDS)]
    assert command[output_r_index : output_r_index + 2] == ["-r", "30"]
    assert "-c:v" in command and command[command.index("-c:v") + 1] == "libx264"
    assert "-c:a" in command and command[command.index("-c:a") + 1] == "aac"
    assert command[-1] == str(output)


def test_subtitle_filter_escapes_filename_and_style_for_ffmpeg(tmp_path: Path):
    subtitle_path = tmp_path / "odd'folder:clip\\take" / "waterleaf-demo.srt"

    expected = (
        "subtitles=filename="
        f"{tmp_path}/odd\\\\\\'folder\\\\:clip\\\\\\\\take/waterleaf-demo.srt:"
        "force_style='FontName=Arial\\,FontSize=30\\,"
        "PrimaryColour=&H00FFFFFF\\,OutlineColour=&H00000000\\,"
        "BorderStyle=1\\,Outline=3\\,Shadow=0\\,MarginV=55\\,Alignment=2'"
    )

    assert _subtitle_filter(subtitle_path) == expected


def test_subtitle_filter_handles_special_characters_with_bundled_ffmpeg(tmp_path: Path):
    imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")
    assets_directory = tmp_path / "odd'folder:clip\\take"
    try:
        assets_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        pytest.skip(f"platform cannot create required subtitle path: {exc}")

    subtitle_path = assets_directory / "waterleaf-demo.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:00,900\nWaterleaf\n",
        encoding="utf-8",
    )
    output = tmp_path / "frame.png"

    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-hide_banner",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=1",
            "-vf",
            _subtitle_filter(subtitle_path),
            "-frames:v",
            "1",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()


def test_parse_probe_reads_duration_and_codecs():
    probe = parse_probe(
        """
        Duration: 00:00:30.02, start: 0.000000, bitrate: 1450 kb/s
        Stream #0:0: Video: h264 (High), yuv420p, 1920x1080, 30 fps
        Stream #0:1: Audio: aac (LC), 48000 Hz, stereo
        """
    )

    assert probe == MediaProbe(duration_seconds=30.02, has_h264=True, has_aac=True)


def test_parse_probe_rejects_missing_duration_and_detects_missing_codecs():
    with pytest.raises(ValueError, match="duration"):
        parse_probe("Stream #0:0: Video: h264")

    probe = parse_probe(
        """
          duration : 00:00:28.00, start: 0.000000, bitrate: 160 kb/s
          Stream #0:0: Audio: mp3, 44100 Hz, mono
        """
    )

    assert probe == MediaProbe(duration_seconds=28.0, has_h264=False, has_aac=False)


def test_validation_accepts_approved_ranges_and_rejects_invalid_media():
    validate_demo(MediaProbe(30.0, has_h264=True, has_aac=True))
    validate_voiceover(MediaProbe(28.0, has_h264=False, has_aac=False))

    with pytest.raises(ValueError, match="29.5-30.2"):
        validate_demo(MediaProbe(31.0, has_h264=True, has_aac=True))
    with pytest.raises(ValueError, match="H.264"):
        validate_demo(MediaProbe(30.0, has_h264=False, has_aac=True))
    with pytest.raises(ValueError, match="AAC"):
        validate_demo(MediaProbe(30.0, has_h264=True, has_aac=False))
    with pytest.raises(ValueError, match="24.0-29.5"):
        validate_voiceover(MediaProbe(30.0, has_h264=False, has_aac=False))


def test_cli_missing_inputs_reports_every_required_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
):
    raw_directory = tmp_path / "raw"
    assets_directory = tmp_path / "assets"
    output = tmp_path / "render" / "waterleaf-demo.mp4"

    called = {"locate": 0, "probe": 0, "run": 0}

    monkeypatch.setattr(
        "scripts.compose_demo.locate_ffmpeg",
        lambda: called.__setitem__("locate", called["locate"] + 1),
    )
    monkeypatch.setattr(
        "scripts.compose_demo.probe_media",
        lambda *args, **kwargs: called.__setitem__("probe", called["probe"] + 1),
    )
    monkeypatch.setattr(
        "scripts.compose_demo.subprocess.run",
        lambda *args, **kwargs: called.__setitem__("run", called["run"] + 1),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "compose_demo.py",
            "--raw-dir",
            str(raw_directory),
            "--assets-dir",
            str(assets_directory),
            "--output",
            str(output),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    assert called == {"locate": 0, "probe": 0, "run": 0}

    stderr = capsys.readouterr().err.splitlines()
    assert stderr == [
        "Missing submission inputs:",
        str(raw_directory / "01-hook.mp4"),
        str(raw_directory / "02-identify.mp4"),
        str(raw_directory / "03-plan.mp4"),
        str(raw_directory / "04-calendar.mp4"),
        str(assets_directory / "waterleaf-end-card.png"),
        str(assets_directory / "waterleaf-voiceover.mp3"),
        str(assets_directory / "waterleaf-demo.srt"),
    ]


def test_cli_happy_path_validates_voiceover_and_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
):
    raw_directory = tmp_path / "raw"
    assets_directory = tmp_path / "assets"
    output = tmp_path / "nested" / "waterleaf-demo.mp4"
    raw_directory.mkdir()
    assets_directory.mkdir()

    for name, _ in RAW_CLIPS:
        (raw_directory / name).write_bytes(b"clip")
    for name in ("waterleaf-end-card.png", "waterleaf-voiceover.mp3", "waterleaf-demo.srt"):
        (assets_directory / name).write_bytes(b"asset")

    seen = {"ffmpeg": None, "probe_paths": [], "command": None}

    def fake_locate_ffmpeg() -> str:
        return "/tmp/ffmpeg"

    def fake_probe_media(ffmpeg: str, path: Path) -> MediaProbe:
        seen["ffmpeg"] = ffmpeg
        seen["probe_paths"].append(path)
        if path.name == "waterleaf-voiceover.mp3":
            return MediaProbe(28.0, has_h264=False, has_aac=False)
        return MediaProbe(30.0, has_h264=True, has_aac=True)

    def fake_run(command: list[str], check: bool) -> None:
        seen["command"] = (command, check)

    monkeypatch.setattr("scripts.compose_demo.locate_ffmpeg", fake_locate_ffmpeg)
    monkeypatch.setattr("scripts.compose_demo.probe_media", fake_probe_media)
    monkeypatch.setattr("scripts.compose_demo.subprocess.run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "compose_demo.py",
            "--raw-dir",
            str(raw_directory),
            "--assets-dir",
            str(assets_directory),
            "--output",
            str(output),
        ],
    )

    main()

    assert output.parent.is_dir()
    assert seen["ffmpeg"] == "/tmp/ffmpeg"
    assert seen["probe_paths"] == [assets_directory / "waterleaf-voiceover.mp3", output]
    assert seen["command"] is not None
    command, check = seen["command"]
    assert check is True
    assert command == compose_command(
        ffmpeg="/tmp/ffmpeg",
        raw_directory=raw_directory,
        assets_directory=assets_directory,
        output=output,
    )
    assert capsys.readouterr().out == f"validated: {output} (30.00s, H.264, AAC)\n"
