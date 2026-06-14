# Waterleaf Hackathon Submission Design

**Date:** June 14, 2026

**Deadline:** June 15, 2026. The official hackathon page does not state a
cutoff time, so required submission assets take priority over optional evidence.

## Objective

Prepare a truthful, cohesive submission package for Waterleaf:

- a 30-second LinkedIn-native demo video;
- a LinkedIn social post;
- published Field Notes;
- evidence for the Backyard AI main track, Llama Champion badge,
  Modal-powered award category, and Field Notes badge;
- final public links and a release checklist.

Waterleaf's core message is:

> A garden photo should become something useful. Waterleaf turns it into an
> editable watering plan and a calendar reminder that still carries the visual
> context of the plant.

## Submission Positioning

The package leads with the user's outcome, then proves the model and runtime
inside the story.

The narrative has four beats:

1. A plant-identification answer is disposable unless it becomes an action.
2. Gemma 4 extracts visible traits, but the model is not the taxonomy database
   and does not make the final species decision.
3. Deterministic rules combine care baselines, planting context, and weather
   data into editable watering dates.
4. The ICS export puts those dates, the plant profile, and the image into the
   gardener's existing calendar workflow.

The video and LinkedIn post must explain the transformation before describing
the stack.

## Claims and Evidence

### Claims to make

- **Backyard AI:** Waterleaf solves an outdoor garden workflow rather than
  presenting a generic chat interface.
- **Llama Champion:** Gemma 4 26B-A4B in GGUF format runs through a pinned
  llama.cpp server. The client sends multimodal inputs, uses strict JSON
  schemas, and enables a bounded thinking pass for candidate reranking.
- **Modal-powered:** The llama.cpp GPU service runs behind a protected Modal
  web endpoint.
- **Field Notes:** The report documents the product problem, grounded
  identification pipeline, llama.cpp configuration, deterministic scheduling,
  portability, tests, observed limitations, and lessons learned.
- **Show, Don't Tell:** The submission includes a short native video and a
  LinkedIn post that show the working transformation.

### Claims not to make

- Do not claim the **Off the Grid** badge. Production inference runs on Modal,
  while taxonomy, geocoding, and weather use GBIF and Open-Meteo.
- Do not call the production product fully local or offline.
- Do not publish a gardener quote or claim user validation. No genuine gardener
  tested Waterleaf before submission.
- Do not publish identification accuracy without a completed, real, labeled
  evaluation set.
- Do not publish latency without a captured, repeatable live measurement.
- Do not say that the language model chooses watering dates. The schedule is
  deterministic, transparent, and editable.

## Evidence Baseline

The following evidence existed when this design was approved:

- the public Space root and `/health` endpoint returned HTTP 200;
- `/health` returned `{"status":"ok"}`;
- all 40 automated tests passed;
- Ruff reported no issues;
- repository code and tests cover multimodal llama.cpp requests, constrained
  schemas, grounded candidate reranking, deterministic scheduling, privacy
  boundaries, persistence, public profiles, and ICS generation.

Before capture, record one successful live plant-identification run and one
complete save/export/profile flow. Optional latency or accuracy evidence must
not delay the required submission assets.

## Licensed Sample Image

Use a real garden-lavender image as the demo input:

- **Title:** "Lavender plants growing in a garden."
- **Photographer:** Brooke Balentine
- **Source:** <https://unsplash.com/photos/lavender-plants-growing-in-a-garden-o-8pxOIAJcg>
- **License:** Unsplash License

Present this as a licensed sample image. Never imply that it came from a
Waterleaf user or from user research. Include attribution in Field Notes and
the repository's submission documentation. The LinkedIn post may include a
compact attribution line if the image is visible outside the app recording.

## Demo Video

### Format

- Platform: LinkedIn native video
- Duration: 30 seconds
- Canvas: 1920x1080, 16:9
- Frame rate: 30 fps
- Export: MP4, H.264 video, AAC audio
- Captions: concise burned-in captions plus a matching SRT file
- Thumbnail: "Photo -> Watering calendar"
- Safe zones: keep important text, logos, and controls away from every edge
- End card: product name, stack, claimed categories, public links, and
  "AI-generated narration"

The video must remain understandable during muted autoplay.

### Storyboard

#### 0-4 seconds: Outcome hook

Show a calendar reminder beside the lavender photo, then cut or rewind into
Waterleaf.

On-screen caption:

> Turn a garden photo into a watering plan.

Voiceover:

> A garden photo should become something useful.

#### 4-11 seconds: Identify

Upload the licensed lavender photo. Cut directly to visible traits and three
database-backed species matches. Do not show upload waiting time or type every
field in real time.

Voiceover:

> Waterleaf uses Gemma 4 through llama.cpp to read visible traits, then grounds
> its suggestions in GBIF records...

#### 11-19 seconds: Confirm and plan

Select English lavender and reveal the editable 30-day schedule with weather
or care-baseline reasons.

On-screen caption:

> The model suggests. You confirm.

Voiceover:

> ...so you make the final call. It combines local care baselines with weather
> rules to create an editable thirty-day plan.

#### 19-26 seconds: Ship the outcome

Save the plant, generate the ICS file, and show a calendar event plus the
linked public plant profile.

Voiceover:

> Save the plant, export the calendar, and every reminder links back to the
> photo.

#### 26-30 seconds: Technical proof

Show a static end card:

- Waterleaf
- Gemma 4 GGUF
- llama.cpp
- Modal
- Gradio
- Backyard AI
- Llama Champion
- Field Notes
- Space and Field Notes links
- AI-generated narration

Voiceover:

> Built with Gradio, llama.cpp, and Modal.

### Full Voiceover

The approved 64-word script is:

> A garden photo should become something useful. Waterleaf uses Gemma 4 through
> llama.cpp to read visible traits, then grounds its suggestions in GBIF records
> so you make the final call. It combines local care baselines with weather
> rules to create an editable thirty-day plan. Save the plant, export the
> calendar, and every reminder links back to the photo. Built with Gradio,
> llama.cpp, and Modal.

### AI Voice

Generate the prerecorded narration with the request-based OpenAI Speech API,
not the Realtime API:

- model: `gpt-4o-mini-tts-2025-12-15`;
- preferred voice: `marin`;
- direction: calm, concise, confident, natural, and not rushed;
- output: WAV or high-quality MP3 for editing.

OpenAI requires clear disclosure that the voice is AI-generated. Include that
disclosure in the video end card and LinkedIn post.

## LinkedIn Post

Publish the video as a native LinkedIn upload. The post should use this order:

1. Outcome-first hook in the first two lines.
2. One compact paragraph describing photo, grounded confirmation, editable
   plan, and calendar export.
3. One compact engineering paragraph covering Gemma 4 GGUF, llama.cpp, Modal,
   deterministic scheduling, and honest remote dependencies.
4. Links to the Space, Field Notes, and repository.
5. A short AI-voice disclosure and focused hashtags.

The post must not begin with the model name or infrastructure. It should avoid
a long technology inventory and avoid unsupported metrics.

Recommended hashtags:

- `#BuildSmall`
- `#HuggingFace`
- `#Gradio`
- `#llamacpp`
- `#Modal`
- `#LocalAI`

Use `#LocalAI` only in reference to the local-model/runtime approach. Do not
pair it with a claim that Waterleaf is fully offline.

## Field Notes

Replace the current future-facing draft with a completed report organized as:

1. The person-shaped problem, without fabricating a user study.
2. Why identification alone was not enough.
3. The grounded pipeline:
   - visible-trait extraction;
   - candidate names;
   - GBIF resolution;
   - reranking only valid records;
   - user confirmation.
4. Running Gemma 4 GGUF through llama.cpp:
   - pinned server image;
   - 8K context;
   - GPU offload;
   - Flash Attention;
   - Q8 KV cache;
   - strict JSON schemas;
   - bounded thinking for reranking.
5. Why scheduling is deterministic rather than model-generated.
6. Why the final artifact is a portable calendar.
7. Privacy boundaries:
   - image normalization and EXIF removal;
   - rounded coordinates;
   - opaque public slugs;
   - public profile limitations.
8. Evidence:
   - automated test count and lint result;
   - live Space health;
   - captured end-to-end flow;
   - latency only if measured;
   - accuracy only if a real evaluation is completed.
9. Failure modes and limitations:
   - model ambiguity;
   - dependence on external taxonomy and weather;
   - fallback to seasonal estimates;
   - manual care interval for unknown plants;
   - calendar-client attachment differences.
10. What was learned:
    - constrain the model to observations;
    - ground names in a taxonomy service;
    - keep scheduling deterministic;
    - make every AI output correctable;
    - optimize the demo around the artifact, not the form.

Include the architecture diagram, selected screenshots, licensed-image
attribution, Space link, repository link, and video link.

## Production Sequence

### 1. Lock evidence

- Verify the deployed Space and health endpoint.
- Run tests and lint.
- Complete one live identification.
- Save one plant.
- Generate and inspect one ICS file.
- Open the public profile and image links.
- Capture only metrics that can be reproduced.

### 2. Capture assets

- Download and record attribution for the licensed lavender image.
- Record the five storyboard clips at 1920x1080.
- Capture the imported or opened calendar event.
- Capture the public plant profile.
- Create the end card and thumbnail.

### 3. Assemble deliverables

- Generate the AI voiceover.
- Edit the 30-second video.
- Create and validate burned captions and SRT.
- Finish and publish Field Notes.
- Finalize the LinkedIn post with working links.

### 4. Release and submit

- Watch the video once muted and once with audio.
- Check it at mobile size.
- Verify spelling, caption timing, safe zones, and disclosure.
- Open every public link in a signed-out session.
- Publish Field Notes before the LinkedIn post so the post can link to it.
- Publish the LinkedIn native video and post.
- Submit the Space, video/post, and Field Notes links.

## QA Gates

The package is ready only when:

- the video duration is at or below 30 seconds;
- the transformation is understandable without audio;
- the narration fits without rushed delivery;
- every model/runtime claim is supported by code or tests;
- no offline, accuracy, latency, or user-validation claim is unsupported;
- licensed-image attribution is present;
- AI-generated narration is disclosed;
- the Space, public profile, media, Field Notes, and repository links work;
- the LinkedIn post and video match the same positioning;
- the submission checklist contains no unresolved required item.

## Scope Boundary

This submission effort does not include:

- redesigning the production architecture for Off the Grid eligibility;
- implementing a fully local model runtime;
- replacing GBIF or Open-Meteo with bundled datasets;
- inventing a user quote;
- building a large evaluation dataset at the expense of required assets;
- unrelated product refactoring.
