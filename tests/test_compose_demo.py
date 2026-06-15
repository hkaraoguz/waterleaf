from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
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


def _decode_video_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    matches = re.findall(r"time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", result.stderr)
    assert matches, result.stderr
    hours, minutes, seconds = matches[-1]
    return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)


def _write_required_inputs(raw_directory: Path, assets_directory: Path) -> None:
    raw_directory.mkdir()
    assets_directory.mkdir()
    for name, _ in RAW_CLIPS:
        (raw_directory / name).write_bytes(b"clip")
    for name in ("waterleaf-end-card.png", "waterleaf-voiceover.mp3", "waterleaf-demo.srt"):
        (assets_directory / name).write_bytes(b"asset")


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
            f"[{index}:v]tpad=stop_mode=clone:stop_duration={duration},"
            f"trim=duration={duration},"
            "setpts=PTS-STARTPTS,"
            "setsar=1,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14241a,"
            "fps=30,format=yuv420p"
            f"[v{index}]"
        ) in filter_complex

    assert "[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0[base]" in filter_complex
    assert "subtitles=filename=" in filter_complex
    assert "force_style='FontName=Arial\\,FontSize=22\\," in filter_complex
    assert "Outline=2\\,Shadow=0\\,MarginV=40\\,Alignment=2'" in filter_complex
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
    assert command[command.index("-af") : command.index("-af") + 2] == [
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
    ]
    assert "-c:a" in command and command[command.index("-c:a") + 1] == "aac"
    assert command[-1] == str(output)


def test_subtitle_filter_escapes_filename_and_style_for_ffmpeg(tmp_path: Path):
    subtitle_path = tmp_path / "odd'folder:clip\\take" / "waterleaf-demo.srt"

    expected = (
        "subtitles=filename="
        f"{tmp_path}/odd\\\\\\'folder\\\\:clip\\\\\\\\take/waterleaf-demo.srt:"
        "force_style='FontName=Arial\\,FontSize=22\\,"
        "PrimaryColour=&H00FFFFFF\\,OutlineColour=&H00000000\\,"
        "BorderStyle=1\\,Outline=2\\,Shadow=0\\,MarginV=40\\,Alignment=2'"
    )

    assert _subtitle_filter(subtitle_path) == expected


@pytest.mark.parametrize(
    ("relative_dir", "expected_fragment"),
    [
        ("comma,dir", "comma\\,dir"),
        ("semi;dir", "semi\\;dir"),
        ("left[dir", "left\\[dir"),
        ("right]dir", "right\\]dir"),
        (
            "mix,;[]'colon:back\\slash",
            "mix\\,\\;\\[\\]\\\\\\'colon\\\\:back\\\\\\\\slash",
        ),
    ],
)
def test_subtitle_filter_escapes_filtergraph_punctuation(
    tmp_path: Path,
    relative_dir: str,
    expected_fragment: str,
):
    subtitle_path = tmp_path / relative_dir / "waterleaf-demo.srt"

    expected = (
        "subtitles=filename="
        f"{tmp_path}/{expected_fragment}/waterleaf-demo.srt:"
        "force_style='FontName=Arial\\,FontSize=22\\,"
        "PrimaryColour=&H00FFFFFF\\,OutlineColour=&H00000000\\,"
        "BorderStyle=1\\,Outline=2\\,Shadow=0\\,MarginV=40\\,Alignment=2'"
    )

    assert _subtitle_filter(subtitle_path) == expected


@pytest.mark.parametrize(
    "relative_dir",
    [
        "comma,dir",
        "semi;dir",
        "left[dir",
        "right]dir",
        "mix,;[]'colon:back\\slash",
    ],
)
def test_subtitle_filter_handles_special_characters_with_bundled_ffmpeg(
    tmp_path: Path,
    relative_dir: str,
):
    assets_directory = tmp_path / relative_dir
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


def test_bundled_ffmpeg_concat_succeeds_with_heterogeneous_sar(tmp_path: Path):
    output = tmp_path / "joined.mp4"
    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-hide_banner",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=30:d=1,setsar=1",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=30:d=1,setsar=2",
            "-filter_complex",
            (
                "[0:v]tpad=stop_mode=clone:stop_duration=1,trim=duration=1,"
                "setpts=PTS-STARTPTS,setsar=1,scale=160:90:force_original_aspect_ratio=decrease,"
                "pad=160:90:(ow-iw)/2:(oh-ih)/2:color=0x14241a,fps=30,format=yuv420p[v0];"
                "[1:v]tpad=stop_mode=clone:stop_duration=1,trim=duration=1,"
                "setpts=PTS-STARTPTS,setsar=1,scale=160:90:force_original_aspect_ratio=decrease,"
                "pad=160:90:(ow-iw)/2:(oh-ih)/2:color=0x14241a,fps=30,format=yuv420p[v1];"
                "[v0][v1]concat=n=2:v=1:a=0[v]"
            ),
            "-map",
            "[v]",
            "-frames:v",
            "60",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()


def test_bundled_ffmpeg_clones_short_video_to_requested_duration(tmp_path: Path):
    output = tmp_path / "short-padded.mp4"
    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-hide_banner",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=30:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo:d=4",
            "-filter_complex",
            (
                "[0:v]tpad=stop_mode=clone:stop_duration=4,trim=duration=4,"
                "setpts=PTS-STARTPTS,setsar=1,scale=320:240:force_original_aspect_ratio=decrease,"
                "pad=320:240:(ow-iw)/2:(oh-ih)/2:color=0x14241a,fps=30,format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-map",
            "1:a:0",
            "-t",
            "4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert _decode_video_duration_seconds(output) == pytest.approx(4.0, abs=0.2)


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
    with pytest.raises(ValueError, match="Last output: .*Impossible to open.*demo\\.mp4"):
        parse_probe(
            "\n".join(
                [
                    "ffmpeg version 7.1",
                    "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'demo.mp4':",
                    "  Metadata:",
                    "  moov atom not found",
                    "Impossible to open 'demo.mp4'",
                ]
            )
        )

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

    with pytest.raises(ValueError, match="29.5-30.0"):
        validate_demo(MediaProbe(31.0, has_h264=True, has_aac=True))
    with pytest.raises(ValueError, match="H.264"):
        validate_demo(MediaProbe(30.0, has_h264=False, has_aac=True))
    with pytest.raises(ValueError, match="AAC"):
        validate_demo(MediaProbe(30.0, has_h264=True, has_aac=False))
    with pytest.raises(ValueError, match="24.0-29.5"):
        validate_voiceover(MediaProbe(30.0, has_h264=False, has_aac=False))


def test_validation_rejects_demo_over_thirty_seconds():
    with pytest.raises(ValueError, match="29.5-30.0"):
        validate_demo(MediaProbe(30.01, has_h264=True, has_aac=True))


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
    _write_required_inputs(raw_directory, assets_directory)

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
        Path(command[-1]).write_bytes(b"rendered")

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
    assert output.read_bytes() == b"rendered"
    assert seen["ffmpeg"] == "/tmp/ffmpeg"
    assert seen["probe_paths"] == [
        assets_directory / "waterleaf-voiceover.mp3",
        output.with_suffix(".tmp.mp4"),
    ]
    assert seen["command"] is not None
    command, check = seen["command"]
    assert check is True
    assert command == compose_command(
        ffmpeg="/tmp/ffmpeg",
        raw_directory=raw_directory,
        assets_directory=assets_directory,
        output=output.with_suffix(".tmp.mp4"),
    )
    assert not output.with_suffix(".tmp.mp4").exists()
    assert capsys.readouterr().out == f"validated: {output} (30.00s, H.264, AAC)\n"


@pytest.mark.parametrize("failure_mode", ["subprocess", "validation"])
def test_cli_failure_preserves_existing_output_and_cleans_temp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_mode: str,
):
    raw_directory = tmp_path / "raw"
    assets_directory = tmp_path / "assets"
    output = tmp_path / "nested" / "waterleaf-demo.mp4"
    _write_required_inputs(raw_directory, assets_directory)
    output.parent.mkdir(parents=True)
    output.write_bytes(b"existing-valid-output")
    temp_output = output.with_suffix(".tmp.mp4")

    def fake_locate_ffmpeg() -> str:
        return "/tmp/ffmpeg"

    def fake_probe_media(ffmpeg: str, path: Path) -> MediaProbe:
        if path.name == "waterleaf-voiceover.mp3":
            return MediaProbe(28.0, has_h264=False, has_aac=False)
        if failure_mode == "validation":
            return MediaProbe(31.0, has_h264=True, has_aac=True)
        raise AssertionError("probe_media should not validate temp output after subprocess failure")

    def fake_run(command: list[str], check: bool) -> None:
        Path(command[-1]).write_bytes(b"temp-render")
        if failure_mode == "subprocess":
            raise subprocess.CalledProcessError(returncode=1, cmd=command)

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

    expected = subprocess.CalledProcessError if failure_mode == "subprocess" else ValueError
    with pytest.raises(expected):
        main()

    assert output.read_bytes() == b"existing-valid-output"
    assert not temp_output.exists()
