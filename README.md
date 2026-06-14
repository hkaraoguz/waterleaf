---
title: Waterleaf
emoji: 🌿
colorFrom: green
colorTo: red
sdk: docker
app_port: 7860
hf_oauth: true
hf_oauth_expiration_minutes: 43200
license: mit
---

# Waterleaf

Waterleaf identifies an outdoor garden plant from one to three photographs,
grounds the result in a plant taxonomy database, builds an editable
weather-aware watering plan, and exports one 30-day calendar for the garden.

Built by Hakan Karaoguz (`hkaraoguz`) for the 2026 Hugging Face Build Small
Hackathon.

## Workflow

1. Upload or capture one to three photographs of one plant.
2. Gemma 4 extracts visible traits and proposes likely names.
3. GBIF resolves those names to valid plant species.
4. Gemma reranks only the valid records.
5. Confirm or replace the species through autocomplete.
6. Preview weather-adjusted dates and edit them.
7. Save plants and export one whole-garden ICS file.

## Architecture

- **UI and web:** Gradio Blocks mounted in FastAPI
- **Authentication:** Hugging Face OAuth
- **Persistence:** SQLite and normalized JPEGs on an attached HF Storage Bucket
- **Vision model:** `ggml-org/gemma-4-26B-A4B-it-GGUF`
- **Runtime:** llama.cpp `server-cuda13-b9445` on a Modal L4
- **Taxonomy:** GBIF Species API
- **Care data:** Perenual, with persistent caching and manual interval fallback
- **Weather:** Open-Meteo geocoding and 16-day forecast
- **Calendar:** RFC 5545-compatible ICS with stable UIDs, alarms, profile URLs,
  and image attachments

See [docs/architecture.md](docs/architecture.md) for the data flow and privacy
boundaries.

## Local Development

Python 3.11-3.13 and `uv` are supported.

```bash
uv sync
uv run uvicorn app:app --host 0.0.0.0 --port 7860
```

Open `http://localhost:7860`. Without `MODAL_ENDPOINT`, Waterleaf uses a
deterministic lavender demo identifier. Local persistence uses the
`local-gardener` identity and `data/` directory.

Run checks:

```bash
uv run pytest
uv run ruff check .
```

## Modal Deployment

### 1. Authenticate the Modal CLI

Install the deploy dependency and connect the local CLI to the Modal workspace:

```bash
uv sync --group deploy
uv run --group deploy modal setup
```

### 2. Deploy llama.cpp

Deploy the protected GPU service:

```bash
uv run --group deploy modal deploy modal_app.py
```

The Modal service:

- uses the pinned `ghcr.io/ggml-org/llama.cpp:server-cuda13-b9445` image;
- starts `Gemma 4 26B-A4B Q4_K_M` with automatic multimodal projector download;
- uses an 8K context, full GPU offload, Flash Attention, Q8 KV cache, and one
  parallel slot;
- uses a bounded 256-token thinking pass for database-candidate reranking while
  keeping initial visual extraction non-thinking and schema-constrained;
- caches Hugging Face artifacts in a Modal Volume;
- requires Modal proxy-auth headers.

The command prints the `modal.run` URL. Save it as `MODAL_ENDPOINT`.

For the live demo and judging window, keep one container warm:

```bash
MODAL_MIN_CONTAINERS=1 uv run --group deploy modal deploy modal_app.py
```

Return to zero warm containers after judging to stop idle GPU spend:

```bash
MODAL_MIN_CONTAINERS=0 uv run --group deploy modal deploy modal_app.py
```

### 3. Create proxy credentials

In Modal Workspace Settings, create a **Web endpoint proxy auth token**. Save
the token ID as `MODAL_KEY` and token secret as `MODAL_SECRET`. These are not
the same credentials used by `modal setup`.

Test the endpoint before configuring the Space:

```bash
MODAL_ENDPOINT=https://...modal.run \
MODAL_KEY=wk-... \
MODAL_SECRET=ws-... \
uv run python scripts/smoke_modal.py assets/sample-lavender.png
```

If a proxy token has not been created yet, a controlled one-time smoke test can
temporarily publish the endpoint:

```bash
MODAL_PROXY_AUTH=0 MODAL_MIN_CONTAINERS=1 \
  uv run --group deploy modal deploy modal_app.py
MODAL_ENDPOINT=https://...modal.run \
  uv run python scripts/smoke_modal.py assets/sample-lavender.png
MODAL_PROXY_AUTH=1 MODAL_MIN_CONTAINERS=0 \
  uv run --group deploy modal deploy modal_app.py
```

The middle deployment is unauthenticated and should exist only for the smoke
test. Always run the final restore command immediately afterward.

## Space Configuration

### 1. Create the Space

Create `build-small-hackathon/waterleaf` in the Hugging Face UI with:

- **SDK:** Docker
- **Visibility:** Public
- **License:** MIT

If the hackathon organization does not allow direct creation, create
`hkaraoguz/waterleaf` first and transfer or duplicate it into the requested
hackathon namespace.

The root README metadata already enables Docker on port `7860` and HF OAuth.

### 2. Upload this repository

Authenticate the Hugging Face CLI and upload the working tree. The CLI sends
binary assets through Xet storage, which a plain Git push does not:

```bash
hf auth login
hf upload build-small-hackathon/waterleaf . . \
  --repo-type space \
  --exclude '.git/**' \
  --exclude '.venv/**' \
  --exclude '.pytest_cache/**' \
  --exclude '.ruff_cache/**' \
  --exclude '**/__pycache__/**' \
  --exclude '*.pyc' \
  --exclude 'data/**' \
  --exclude '.env'
```

Do not commit or upload local environment files or deployment secrets.

### 3. Attach persistent storage

In **Space Settings → Storage Buckets**:

1. Create or select a bucket for Waterleaf.
2. Attach it read-write.
3. Set the mount path to `/data`.

The Docker image already sets `WATERLEAF_DATA_DIR=/data`. Without this mount,
saved gardens and images disappear when the Space restarts.

### 4. Configure secrets and variables

In **Space Settings → Variables and secrets**, add:

| Name | Type | Required | Purpose |
| --- | --- | --- | --- |
| `MODAL_ENDPOINT` | Secret | Production | Protected llama.cpp base URL |
| `MODAL_KEY` | Secret | Production | Modal proxy token ID |
| `MODAL_SECRET` | Secret | Production | Modal proxy token secret |
| `PERENUAL_API_KEY` | Secret | Optional | Plant care benchmark lookup |
| `PUBLIC_BASE_URL` | Variable | Optional | Override the derived Space URL |
| `WATERLEAF_DATA_DIR` | Variable | No | Defaults to `/data` in Docker |

Use only the base Modal URL for `MODAL_ENDPOINT`; do not append
`/v1/chat/completions`.

### 5. Rebuild and verify

Trigger **Factory reboot** after attaching storage or changing secrets. Then
verify:

```bash
curl --fail https://build-small-hackathon-waterleaf.hf.space/health
```

Expected response:

```json
{"status":"ok"}
```

Open the Space directly, not only inside the Hub iframe, and check:

1. **Sign in with Hugging Face** completes successfully.
2. A guest can preview one identification.
3. A signed-in user can save a plant and see it after a factory restart.
4. The generated ICS downloads and its public plant/image links open.

Guests may run one temporary identification preview. Login is required to
save, delete, or export plants.

## Evaluation

Populate `evaluation/manifest.csv` with at least 20 consented real-garden
examples and run:

```bash
MODAL_ENDPOINT=... MODAL_KEY=... MODAL_SECRET=... \
  uv run python scripts/evaluate.py evaluation/manifest.csv
```

The report includes species top-1/top-3 accuracy, genus top-1 accuracy,
per-case predictions, and latency. A live one-to-three-photo smoke test is
available at `scripts/smoke_modal.py`.

## Privacy and Limitations

- Images are resized, converted to JPEG, and stripped of EXIF.
- Stored coordinates are rounded and never exposed on public plant pages.
- Public pages use opaque slugs but are intentionally public for calendar use.
- Plant identification and watering dates are suggestions, not horticultural
  guarantees.
- Dates after the 16-day forecast are labeled seasonal estimates.
- ICS `ATTACH` support varies by calendar client; every event also includes a
  portable public profile link.
- Perenual can be omitted; users must provide a manual interval when no care
  benchmark is available.

## Submission Materials

- [Field Notes draft](docs/field-notes.md)
- [Demo script](docs/demo-script.md)
- [Social post draft](docs/social-post.md)
- [Submission checklist](docs/submission-checklist.md)

Target quests: Backyard AI, Llama Champion, Modal-powered, and Field Notes.
Waterleaf does not claim Off the Grid because inference and weather data are
cloud-hosted.

## Credits

- [Gemma 4](https://huggingface.co/google/gemma-4-26B-A4B-it)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [GBIF](https://www.gbif.org/developer/species)
- [Perenual](https://perenual.com/docs/api)
- [Open-Meteo](https://open-meteo.com/)
