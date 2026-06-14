from pathlib import Path

from PIL import Image, ImageDraw

from scripts.submission_assets import (
    CAPTION_CUES,
    END_CARD_LINES,
    VOICEOVER,
    CaptionCue,
    _load_font,
    generate_voiceover,
    main,
    render_end_card,
    render_srt,
    render_thumbnail,
    speech_payload,
    write_static_assets,
)


def test_voiceover_caption_cues_and_srt_are_exact():
    assert VOICEOVER == (
        "A garden photo should become something useful. Waterleaf uses Gemma 4 through llama.cpp "
        "to read visible traits, then grounds its suggestions in GBIF records so you make the "
        "final "
        "call. It combines local care baselines with weather rules to create an editable "
        "thirty-day "
        "plan. Save the plant, export the calendar, and every reminder links back to the photo. "
        "Built with Gradio, llama.cpp, and Modal."
    )
    assert CAPTION_CUES == [
        CaptionCue(
            "00:00:00,000",
            "00:00:04,000",
            "A garden photo should become something useful.",
        ),
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
        CaptionCue(
            "00:00:26,000",
            "00:00:30,000",
            "Built with Gradio, llama.cpp, and Modal.",
        ),
    ]
    assert render_srt() == (
        "1\n"
        "00:00:00,000 --> 00:00:04,000\n"
        "A garden photo should become something useful.\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:11,000\n"
        "Waterleaf uses Gemma 4 through llama.cpp\n"
        "to read visible traits, then grounds its\n"
        "suggestions in GBIF records...\n\n"
        "3\n"
        "00:00:11,000 --> 00:00:19,000\n"
        "...so you make the final call. It combines\n"
        "local care baselines with weather rules to\n"
        "create an editable thirty-day plan.\n\n"
        "4\n"
        "00:00:19,000 --> 00:00:26,000\n"
        "Save the plant, export the calendar,\n"
        "and every reminder links back to the photo.\n\n"
        "5\n"
        "00:00:26,000 --> 00:00:30,000\n"
        "Built with Gradio, llama.cpp, and Modal.\n"
    )


def test_end_card_lines_and_speech_payload_are_exact():
    assert END_CARD_LINES == [
        "Gemma 4 GGUF  |  llama.cpp  |  Modal  |  Gradio",
        "Backyard AI  |  Llama Champion  |  Field Notes",
        "hf.co/spaces/build-small-hackathon/waterleaf",
        "AI-generated narration",
    ]

    payload = speech_payload()
    assert payload == {
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


def test_generate_voiceover_uses_owned_and_injected_clients(monkeypatch, tmp_path):
    destination = tmp_path / "voiceover.mp3"
    bytes_written = b"fake mp3 bytes"

    class OwnedResponse:
        def __init__(self):
            self.content = bytes_written
            self.raised = False

        def raise_for_status(self):
            self.raised = True

    class OwnedClient:
        def __init__(self):
            self.post_calls = []
            self.closed = False
            self.response = OwnedResponse()

        def post(self, url, *, headers, json, timeout):
            self.post_calls.append(
                {
                    "url": url,
                    "headers": headers,
                    "json": json,
                    "timeout": timeout,
                }
            )
            return self.response

        def close(self):
            self.closed = True

    owned_client = OwnedClient()

    class OwnedFactory:
        def __call__(self):
            return owned_client

    monkeypatch.setattr("scripts.submission_assets.httpx.Client", OwnedFactory())

    result = generate_voiceover(destination, "owned-key")

    assert result == destination
    assert destination.read_bytes() == bytes_written
    assert owned_client.response.raised is True
    assert owned_client.closed is True
    assert owned_client.post_calls == [
        {
            "url": "https://api.openai.com/v1/audio/speech",
            "headers": {"Authorization": "Bearer owned-key"},
            "json": speech_payload(),
            "timeout": 120,
        }
    ]

    class InjectedResponse:
        def __init__(self):
            self.content = b"other bytes"
            self.raised = False

        def raise_for_status(self):
            self.raised = True

    class InjectedClient:
        def __init__(self):
            self.closed = False
            self.response = InjectedResponse()
            self.post_calls = []

        def post(self, url, *, headers, json, timeout):
            self.post_calls.append((url, headers, json, timeout))
            return self.response

        def close(self):
            self.closed = True

    injected_client = InjectedClient()
    second_destination = tmp_path / "other.mp3"

    result = generate_voiceover(second_destination, "injected-key", client=injected_client)

    assert result == second_destination
    assert second_destination.read_bytes() == b"other bytes"
    assert injected_client.response.raised is True
    assert injected_client.closed is False
    assert injected_client.post_calls == [
        (
            "https://api.openai.com/v1/audio/speech",
            {"Authorization": "Bearer injected-key"},
            speech_payload(),
            120,
        )
    ]


def test_font_fallback_scales_when_no_candidates(monkeypatch):
    monkeypatch.setattr("scripts.submission_assets._font_candidates", lambda: [])

    canvas = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(canvas)

    small_font = _load_font(18)
    large_font = _load_font(48)
    small_bbox = draw.textbbox((0, 0), "Waterleaf", font=small_font)
    large_bbox = draw.textbbox((0, 0), "Waterleaf", font=large_font)

    assert (large_bbox[3] - large_bbox[1]) > (small_bbox[3] - small_bbox[1]) * 1.5
    assert (large_bbox[2] - large_bbox[0]) > (small_bbox[2] - small_bbox[0]) * 1.5


def test_font_fallback_and_static_asset_rendering_without_candidates(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.submission_assets._font_candidates", lambda: [])

    end_card = render_end_card()
    thumbnail = render_thumbnail()

    assert end_card.size == (1920, 1080)
    assert end_card.mode == "RGB"
    assert thumbnail.size == (1920, 1080)
    assert thumbnail.mode == "RGB"

    outputs = write_static_assets(tmp_path)

    assert outputs == {
        "script": tmp_path / "waterleaf-voiceover.txt",
        "captions": tmp_path / "waterleaf-demo.srt",
        "end_card": tmp_path / "waterleaf-end-card.png",
        "thumbnail": tmp_path / "waterleaf-thumbnail.png",
    }
    assert outputs["script"].read_text() == VOICEOVER + "\n"
    assert outputs["captions"].read_text() == render_srt()
    for key in ("end_card", "thumbnail"):
        with Image.open(outputs[key]) as image:
            assert image.size == (1920, 1080)
            assert image.mode == "RGB"


def test_cli_writes_safe_static_output_and_voiceover(monkeypatch, tmp_path, capsys):
    outputs = {
        "script": tmp_path / "waterleaf-voiceover.txt",
        "captions": tmp_path / "waterleaf-demo.srt",
        "end_card": tmp_path / "waterleaf-end-card.png",
        "thumbnail": tmp_path / "waterleaf-thumbnail.png",
    }

    def fake_write_static_assets(output_directory):
        assert Path(output_directory) == tmp_path
        for path in outputs.values():
            path.write_text("ok")
        return outputs

    recorded = {}

    def fake_generate_voiceover(destination, api_key, client=None):
        recorded["destination"] = destination
        recorded["api_key"] = api_key
        recorded["client"] = client
        destination.write_bytes(b"fake mp3")
        return destination

    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    monkeypatch.setattr("scripts.submission_assets.write_static_assets", fake_write_static_assets)
    monkeypatch.setattr("scripts.submission_assets.generate_voiceover", fake_generate_voiceover)

    main(["--out", str(tmp_path), "--voice"])

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured == [
        f"script: {outputs['script']}",
        f"captions: {outputs['captions']}",
        f"end_card: {outputs['end_card']}",
        f"thumbnail: {outputs['thumbnail']}",
        f"voice: {tmp_path / 'waterleaf-voiceover.mp3'}",
    ]
    assert "secret-key" not in "\n".join(captured)
    assert recorded == {
        "destination": tmp_path / "waterleaf-voiceover.mp3",
        "api_key": "secret-key",
        "client": None,
    }


def test_cli_requires_key_for_voice(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    called = {"generate": False}

    def fake_generate_voiceover(*args, **kwargs):
        called["generate"] = True
        raise AssertionError("generate_voiceover should not be called without a key")

    monkeypatch.setattr(
        "scripts.submission_assets.write_static_assets",
        lambda output_directory: {
            "script": Path(output_directory) / "waterleaf-voiceover.txt",
            "captions": Path(output_directory) / "waterleaf-demo.srt",
            "end_card": Path(output_directory) / "waterleaf-end-card.png",
            "thumbnail": Path(output_directory) / "waterleaf-thumbnail.png",
        },
    )
    monkeypatch.setattr("scripts.submission_assets.generate_voiceover", fake_generate_voiceover)

    try:
        main(["--out", str(tmp_path), "--voice"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("main() did not exit when OPENAI_API_KEY was missing")
    assert called["generate"] is False


def test_cli_defaults_to_artifacts_submission_and_prints_safe_paths(monkeypatch, capsys):
    captured = {}

    def fake_write_static_assets(output_directory):
        captured["output_directory"] = Path(output_directory)
        return {
            "script": Path("artifacts/submission/waterleaf-voiceover.txt"),
            "captions": Path("artifacts/submission/waterleaf-demo.srt"),
            "end_card": Path("artifacts/submission/waterleaf-end-card.png"),
            "thumbnail": Path("artifacts/submission/waterleaf-thumbnail.png"),
        }

    monkeypatch.setattr("scripts.submission_assets.write_static_assets", fake_write_static_assets)

    main([])

    assert captured["output_directory"] == Path("artifacts/submission")
    assert capsys.readouterr().out.strip().splitlines() == [
        "script: artifacts/submission/waterleaf-voiceover.txt",
        "captions: artifacts/submission/waterleaf-demo.srt",
        "end_card: artifacts/submission/waterleaf-end-card.png",
        "thumbnail: artifacts/submission/waterleaf-thumbnail.png",
    ]
