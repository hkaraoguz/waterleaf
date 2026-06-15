# Waterleaf 30-Second Demo Script

## Output

- LinkedIn native
- 1920x1080, 16:9, 30 fps
- H.264/AAC MP4
- Maximum 30 seconds
- Burned captions plus `artifacts/submission/waterleaf-demo.srt`
- AI narration disclosure on the end card and in the post copy

Record clean clips without notifications, browser chrome changes, or visible
secrets. Each source clip may be longer than its final duration because the
composition script trims it.
Keep secrets and account menus out of frame.

## Raw Clips

1. `artifacts/submission/raw/01-hook.mp4` - 4 sec
   Public plant profile with the licensed lavender image and upcoming watering
   dates.
2. `artifacts/submission/raw/02-identify.mp4` - 7 sec
   Licensed image to visible traits and three GBIF-backed matches. Waiting can
   be recorded raw but cut out.
3. `artifacts/submission/raw/03-plan.mp4` - 8 sec
   Confirm English lavender. Reveal editable dates, reason, and confidence.
4. `artifacts/submission/raw/04-calendar.mp4` - 7 sec
   Show the saved plant card, generated ICS file, and public profile.
5. `artifacts/submission/waterleaf-end-card.png` - 4 sec
   Generated end card.

## Timeline

- `0-4`
  - Visual: public plant profile with the lavender image and upcoming dates.
  - Caption: `Turn a garden photo into a watering plan.`
  - Voice: `A garden photo should become something useful.`
- `4-11`
  - Visual: upload the licensed image, show visible traits, then the three
    GBIF-backed matches.
  - Voice: `Waterleaf uses Gemma 4 through llama.cpp to read visible traits,
    then grounds its suggestions in GBIF records...`
- `11-19`
  - Visual: confirm English lavender and reveal editable dates with reason and
    confidence.
  - Caption: `The model suggests. You confirm.`
  - Voice: `...so you make the final call. It combines local care baselines
    with weather rules to create an editable thirty-day plan.`
- `19-26`
  - Visual: saved plant card, generated ICS file, then the public plant
    profile.
  - Voice: `Save the plant, export the calendar, and every reminder links back to the photo.`
- `26-30`
  - Visual: `artifacts/submission/waterleaf-end-card.png`
  - End card stack:
    `Gemma 4 GGUF  |  llama.cpp  |  Modal  |  Gradio`
    `Backyard AI  |  Llama Champion  |  Field Notes`
    `hf.co/spaces/build-small-hackathon/waterleaf`
    `AI-generated narration`
  - Voice: `Built with Gradio, llama.cpp, and Modal.`

## Full Voiceover

`A garden photo should become something useful. Waterleaf uses Gemma 4 through
llama.cpp to read visible traits, then grounds its suggestions in GBIF records
so you make the final call. It combines local care baselines with weather
rules to create an editable thirty-day plan. Save the plant, export the
calendar, and every reminder links back to the photo. Built with Gradio,
llama.cpp, and Modal.`

## Editing Rules

- Outcome first.
- Show decisive interactions only.
- No login, deletion flow, or dashboard tour.
- No Off the Grid, fully local, accuracy, latency, or user-validation claims.
- Must still be understandable when muted.
