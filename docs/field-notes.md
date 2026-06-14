# Field Notes: Building Waterleaf with Gemma 4 and llama.cpp

## The person and the problem

Waterleaf is being built for a gardener who recognizes many plants by sight but
does not want to maintain a spreadsheet of watering dates. The useful outcome
is not another plant-identification answer. It is a calendar that can be acted
on and corrected.

## Why a grounded pipeline

A vision-language model can describe leaf shape, flower form, growth habit, and
visible planting context. It should not be the database of record. Waterleaf
therefore asks Gemma 4 for observations and candidate names, resolves those
names through GBIF, and allows Gemma to rerank only valid taxonomy records.
The gardener makes the final choice.

## Running the large model small

The model is Gemma 4 26B-A4B, a mixture-of-experts model with roughly 4B active
parameters per token. It runs as a Q4_K_M GGUF through llama.cpp on a Modal L4.
The container is pinned to a llama.cpp build, uses an 8K context and quantized
KV cache. Initial visual extraction is schema-constrained without thinking.
The database-candidate rerank uses a bounded 256-token thinking pass, with
llama.cpp separating reasoning from the final JSON response.
The Hugging Face Space remains a small CPU application.

## Scheduling without pretending

Watering depends on species, planting context, rain, temperature, and drying
conditions. Waterleaf combines a local care baseline or user-entered interval
with Open-Meteo data. Forecast dates are adjusted with deterministic rules and
shown before export. Dates beyond the reliable forecast window are visibly
marked as seasonal estimates. Users can edit or remove every event.

## Calendar portability

The export is one 30-day ICS file containing individual 15-minute events. Each
event links to a public, location-free plant profile and includes the image as
an ICS attachment. Calendar clients differ in how they display attachments, so
the profile link is the portable visual fallback.

## What to measure before submission

The final report will include at least 20 real garden examples, species top-1
and top-3 accuracy, genus accuracy, correction rate, and warm/cold latency.
It will also document manual imports into Apple Calendar, Google Calendar, and
Outlook, plus feedback from the gardener the project was built for.
