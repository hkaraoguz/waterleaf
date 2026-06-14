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


def test_voiceover_and_caption_cues_have_expected_timing():
    assert len(VOICEOVER.split()) == 64
    assert CAPTION_CUES[0].start == "00:00:00,000"
    assert CAPTION_CUES[-1].end == "00:00:30,000"
    assert render_srt().endswith("Built with Gradio, llama.cpp, and Modal.\n")


def test_end_card_lines_and_speech_payload_match_spec():
    assert "AI-generated narration" in END_CARD_LINES

    payload = speech_payload()
    assert payload["model"] == "gpt-4o-mini-tts-2025-12-15"
    assert payload["voice"] == "marin"
    assert payload["input"] == VOICEOVER
    assert payload["response_format"] == "mp3"
    assert "27 to 29 seconds" in payload["instructions"]
    assert "Do not add or remove words" in payload["instructions"]


def test_generate_voiceover_posts_payload_and_writes_response_bytes(tmp_path):
    bytes_written = b"fake mp3 bytes"

    class FakeResponse:
        def __init__(self, content):
            self.status_checked = False
            self.content = content

        def raise_for_status(self):
            self.status_checked = True

    class FakeClient:
        def __init__(self):
            self.calls = []
            self.closed = False
            self.response = FakeResponse(bytes_written)

        def post(self, url, *, headers, json, timeout):
            self.calls.append(
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

    client = FakeClient()
    destination = tmp_path / "voiceover.mp3"

    result = generate_voiceover(
        destination,
        "test-key",
        client=client,
    )

    assert result == destination
    assert destination.read_bytes() == bytes_written
    assert client.response.status_checked is True
    assert client.closed is False
    assert client.calls == [
        {
            "url": "https://api.openai.com/v1/audio/speech",
            "headers": {"Authorization": "Bearer test-key"},
            "json": speech_payload(),
            "timeout": 120,
        }
    ]


def test_write_static_assets_creates_expected_files(tmp_path):
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
