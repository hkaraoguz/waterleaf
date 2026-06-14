# LinkedIn Post

I built Waterleaf: a garden photo becomes an editable watering calendar.

Upload 1-3 photos, review the visible traits, and confirm a GBIF-backed
species match. Waterleaf combines a local care baseline with transparent
weather rules to produce editable 30-day watering dates, then exports one
calendar for the garden. Every reminder links back to the plant photo.

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

Narration disclosure: AI-generated with OpenAI text-to-speech.

Demo image: "Lavender plants growing in a garden" by Brooke Balentine, Unsplash License.

#BuildSmall #HuggingFace #Gradio #llamacpp #Modal #Gemma
