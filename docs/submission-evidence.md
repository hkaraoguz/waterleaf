# Submission Evidence

Verified June 15, 2026.

## Checks

- `uv run --group demo pytest -q`: 74 passed
- `uv run ruff check .`: all checks passed

## Public Space

- Space URL:
  <https://huggingface.co/spaces/build-small-hackathon/waterleaf>
- Direct app:
  <https://build-small-hackathon-waterleaf.hf.space/>
- Health URL:
  <https://build-small-hackathon-waterleaf.hf.space/health>
- Root returned HTTP 200
- Health returned HTTP 200
- Health body:

```json
{"status":"ok"}
```

## Licensed Demo Input

- File: `assets/demo/lavender-garden-brooke-balentine.jpg`
- Format and dimensions: JPEG, 1920x2880
- Photographer: Brooke Balentine
- Source:
  <https://unsplash.com/photos/lavender-plants-growing-in-a-garden-o-8pxOIAJcg>
- License: Unsplash License
- Attribution record: [ATTRIBUTION.md](../assets/demo/ATTRIBUTION.md)

## Live Analysis And Schedule

A live guest run against the deployed Space completed with the licensed
lavender image:

1. Gemma 4 visual analysis through llama.cpp returned visible flower, leaf,
   stem, and growth-habit traits.
2. GBIF grounding returned three candidates. `Lavandula angustifolia` was the
   top result, followed by `Lavandula intermedia` and `Lavandula latifolia`.
3. Stockholm resolved to the `Europe/Stockholm` timezone.
4. The English lavender care baseline was 7-10 days in full sun.
5. Schedule preview returned five editable events across the 30-day window.

Candidate confidence varied between repeated model runs, so this evidence
records the stable ordering and workflow result rather than a fixed score.

## Submission Assets

- Voiceover: 64 words, 27.22 seconds, OpenAI text-to-speech
- Captions: five burned-caption cues covering 0-30 seconds
- End card: 1920x1080 PNG
- Thumbnail: 1920x1080 PNG
- Demo master: 29.83 seconds, 1920x1080, 30 fps, H.264/AAC MP4
- Demo audio: -15.9 LUFS integrated, -1.4 dBTP true peak
- Final soundtrack transcription matched the approved script at 98.5%;
  the only difference was transcribing `thirty` as `30`.

The demo uses deployed-Space captures for guest image analysis, GBIF candidate
confirmation, and Stockholm schedule preview. Save, ICS export, and public
profile footage was captured from the same application code in an isolated
local data directory because CLI authentication does not create a browser
Hugging Face OAuth profile.

## Claim Boundaries

- Waterleaf can claim Llama Champion.
- Waterleaf can claim Modal-powered.
- Waterleaf does not claim Off the Grid.
- Waterleaf does not claim measured accuracy.
- Waterleaf does not claim measured latency.
- Waterleaf does not claim user validation.

## Live Workflow

A fresh signed-in save/export/profile flow is still pending. It will be
recorded and added here only after live verification. This file does not yet
claim that the authenticated workflow is complete.
