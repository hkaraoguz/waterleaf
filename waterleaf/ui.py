from __future__ import annotations

import html
import json
import os
from datetime import date, time
from pathlib import Path

import gradio as gr

from waterleaf.application import WaterleafApplication
from waterleaf.models import (
    CareProfile,
    IdentificationResult,
    LocationMatch,
    SchedulePlan,
    TaxonCandidate,
    WateringEvent,
)
from waterleaf.rate_limit import SlidingWindowRateLimiter
from waterleaf.services.demo import DemoTaxonomy, build_demo_identification

CSS = """
:root {
  --wl-ink: #18211a;
  --wl-muted: #5c685f;
  --wl-leaf: #2f6b45;
  --wl-leaf-dark: #214c32;
  --wl-coral: #b84e3c;
  --wl-line: #d7dfd5;
  --wl-bg: #f4f7f2;
  --wl-paper: #ffffff;
}
body, .gradio-container { background: var(--wl-bg) !important; color: var(--wl-ink); }
.gradio-container { max-width: 1180px !important; padding: 18px !important; }
#wl-header { border-bottom: 1px solid var(--wl-line); padding: 8px 0 16px; margin-bottom: 12px; }
#wl-header h1 { font-size: 30px; line-height: 1.05; margin: 0; letter-spacing: 0; }
#wl-header p { color: var(--wl-muted); margin: 5px 0 0; }
.wl-section {
  background: var(--wl-paper);
  border: 1px solid var(--wl-line);
  border-radius: 8px;
  padding: 14px;
}
.wl-steps { color: var(--wl-muted); font-size: 13px; text-transform: uppercase; font-weight: 700; }
.wl-status { border-left: 3px solid var(--wl-coral); padding-left: 10px; }
.wl-garden { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; }
.wl-plant {
  border: 1px solid var(--wl-line);
  border-radius: 8px;
  overflow: hidden;
  background: var(--wl-paper);
}
.wl-plant img { width: 100%; aspect-ratio: 4/3; object-fit: cover; display: block; }
.wl-plant-body { padding: 12px; }
.wl-plant h3 { font-size: 17px; margin: 0 0 3px; letter-spacing: 0; }
.wl-plant p { color: var(--wl-muted); margin: 0; }
.wl-empty { border: 1px dashed #aab7a8; padding: 20px; border-radius: 8px; color: var(--wl-muted); }
button.primary { background: var(--wl-leaf) !important; border-color: var(--wl-leaf) !important; }
button.primary:hover { background: var(--wl-leaf-dark) !important; }
@media (max-width: 680px) {
  .gradio-container { padding: 10px !important; }
  #wl-header h1 { font-size: 26px; }
  #wl-export-row, #wl-delete-row {
    flex-direction: column !important;
    flex-wrap: wrap !important;
  }
  #wl-export-row > *, #wl-delete-row > * {
    width: 100% !important;
    min-width: 0 !important;
    flex: 1 1 auto !important;
  }
}
"""


def build_ui(
    application: WaterleafApplication,
    *,
    identification=None,
    taxonomy=None,
    sample_image: str | Path = "assets/sample-lavender.png",
) -> gr.Blocks:
    identification = identification or application.identification or build_demo_identification()
    taxonomy = taxonomy or application.taxonomy or DemoTaxonomy()
    oauth_enabled = bool(os.getenv("SPACE_ID") or os.getenv("OAUTH_CLIENT_ID"))
    guest_limiter = SlidingWindowRateLimiter(limit=3, window_seconds=3600)

    def owner_from_profile(profile: gr.OAuthProfile | None) -> str | None:
        if profile is not None:
            return profile.username
        if not oauth_enabled:
            return os.getenv("WATERLEAF_LOCAL_USER", "local-gardener")
        return None

    def load_dashboard(
        profile: gr.OAuthProfile | None,
    ):
        owner = owner_from_profile(profile)
        return _garden_html(application, owner), _plant_delete_choices(application, owner)

    def analyze_photos(
        image_1,
        image_2,
        image_3,
        guest_used,
        profile: gr.OAuthProfile | None,
        request: gr.Request,
    ):
        if oauth_enabled and profile is None:
            if guest_used:
                raise gr.Error("Sign in to run another plant identification.")
            client_ip = request.client.host if request.client else "unknown"
            if not guest_limiter.allow(client_ip):
                raise gr.Error("Guest identification limit reached. Sign in to continue.")
        paths = [Path(item) for item in [image_1, image_2, image_3] if item]
        if not paths:
            raise gr.Error("Add at least one plant photo.")
        if len(paths) > 3:
            raise gr.Error("Use no more than three photos.")
        result = identification.identify(paths)
        if not result.candidates:
            raise gr.Error("No database-backed species match was found. Use species search.")
        choices = [(_candidate_label(item), item.taxon_key) for item in result.candidates]
        visual = (
            "**Visible traits:** "
            + ", ".join(result.visual.traits)
            + "\n\nModel suggestions are provisional until you confirm a database record."
        )
        return (
            result.model_dump_json(),
            gr.Radio(choices=choices, value=result.candidates[0].taxon_key),
            visual,
            "Container" if result.visual.is_container else "In ground",
            result.visual.size_label.title(),
            bool(guest_used or (oauth_enabled and profile is None)),
        )

    def search_species(query: str):
        matches = taxonomy.suggest(query, limit=10)
        choices = [
            (_candidate_label(item), item.model_dump_json()) for item in matches
        ]
        return gr.Dropdown(choices=choices, value=None)

    def preview(
        candidate_key,
        override_json,
        result_json,
        location_query,
        planting,
        size_label,
        manual_interval,
    ):
        candidate = _selected_candidate(candidate_key, override_json, result_json)
        if not location_query.strip():
            raise gr.Error("Enter a city.")
        try:
            interval_days = _parse_optional_interval(manual_interval)
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc
        plan = application.preview_schedule(
            candidate=candidate,
            location_query=location_query,
            is_container=planting == "Container",
            size_label=size_label.casefold(),
            manual_interval_days=interval_days,
        )
        rows = [
            [item.date.isoformat(), item.reason, item.confidence]
            for item in plan.events
        ]
        care_note = _care_markdown(plan.care, plan.location)
        return _plan_to_json(plan), rows, care_note

    def save(
        image_1,
        nickname,
        preferred_time,
        candidate_key,
        override_json,
        result_json,
        plan_json,
        schedule_rows,
        profile: gr.OAuthProfile | None,
    ):
        owner = owner_from_profile(profile)
        if owner is None:
            raise gr.Error("Sign in with Hugging Face to save this plant.")
        if not image_1:
            raise gr.Error("The first plant photo is required.")
        if not nickname.strip():
            raise gr.Error("Add a plant nickname.")
        candidate = _selected_candidate(candidate_key, override_json, result_json)
        plan = _plan_from_json(plan_json)
        events = _events_from_rows(schedule_rows)
        saved = application.save_plant(
            owner=owner,
            nickname=nickname.strip(),
            candidate=candidate,
            source_image=image_1,
            preferred_time=_parse_time(preferred_time),
            plan=plan,
            edited_events=events,
        )
        return (
            f"Saved **{saved.nickname}**.",
            _garden_html(application, owner),
            _plant_delete_choices(application, owner),
        )

    def export(profile: gr.OAuthProfile | None):
        owner = owner_from_profile(profile)
        if owner is None:
            raise gr.Error("Sign in with Hugging Face to export your garden.")
        path = application.export_garden(owner)
        return str(path), "Calendar generated."

    def delete(selected_id, profile: gr.OAuthProfile | None):
        owner = owner_from_profile(profile)
        if owner is None:
            raise gr.Error("Sign in with Hugging Face to manage saved plants.")
        if not selected_id:
            raise gr.Error("Select a saved plant.")
        if not application.delete_plant(owner, selected_id):
            raise gr.Error("Plant not found.")
        return (
            _garden_html(application, owner),
            _plant_delete_choices(application, owner),
            "Plant deleted.",
        )

    with gr.Blocks(
        title="Waterleaf",
        fill_width=True,
    ) as demo:
        result_state = gr.State("")
        plan_state = gr.State("")
        guest_used_state = gr.State(False)

        with gr.Row(elem_id="wl-header"):
            with gr.Column(scale=5):
                gr.Markdown("# Waterleaf\nGarden watering calendar")
            with gr.Column(scale=2, min_width=210):
                if oauth_enabled:
                    gr.LoginButton(size="sm")
                else:
                    gr.Button(
                        "Sign in with Hugging Face",
                        size="sm",
                        interactive=False,
                    )

        with gr.Tabs():
            with gr.Tab("My garden"):
                garden = gr.HTML(elem_classes="wl-section")
                with gr.Row(elem_id="wl-export-row"):
                    export_button = gr.Button(
                        "Generate 30-day calendar",
                        variant="primary",
                    )
                    calendar_file = gr.File(
                        label="Waterleaf calendar",
                        interactive=False,
                    )
                export_status = gr.Markdown(elem_classes="wl-status")
                with gr.Row(elem_id="wl-delete-row"):
                    delete_choice = gr.Dropdown(
                        label="Saved plant",
                        choices=[],
                        filterable=True,
                    )
                    delete_button = gr.Button("Delete plant", variant="stop")
                delete_status = gr.Markdown()
                gr.Image(
                    value=str(sample_image),
                    label="Example: Patio lavender",
                    height=260,
                    interactive=False,
                    buttons=["fullscreen"],
                )

            with gr.Tab("Add plant"):
                gr.Markdown("Capture", elem_classes="wl-steps")
                with gr.Row(equal_height=True):
                    image_1 = gr.Image(
                        label="Plant photo (required)",
                        type="filepath",
                        sources=["upload", "webcam"],
                        height=260,
                    )
                    image_2 = gr.Image(
                        label="Leaf or flower detail",
                        type="filepath",
                        sources=["upload", "webcam"],
                        height=260,
                    )
                    image_3 = gr.Image(
                        label="Second angle",
                        type="filepath",
                        sources=["upload", "webcam"],
                        height=260,
                    )
                analyze_button = gr.Button("Analyze photos", variant="primary")

                gr.Markdown("Confirm species", elem_classes="wl-steps")
                visual_summary = gr.Markdown(elem_classes="wl-section")
                candidates = gr.Radio(
                    label="Database match (required)",
                    choices=[],
                )
                with gr.Row():
                    species_search = gr.Textbox(
                        label="Search common or scientific name",
                        placeholder="Lavandula angustifolia",
                    )
                    species_override = gr.Dropdown(
                        label="Replace identification",
                        choices=[],
                        filterable=True,
                    )

                gr.Markdown("Schedule", elem_classes="wl-steps")
                with gr.Row():
                    nickname = gr.Textbox(
                        label="Plant nickname (required)",
                        placeholder="Patio lavender",
                    )
                    location = gr.Textbox(
                        label="City (required)",
                        placeholder="Stockholm, Sweden",
                    )
                    preferred_time = gr.Textbox(
                        label="Watering time (required)",
                        value="07:30",
                    )
                with gr.Row():
                    planting = gr.Radio(
                        label="Planting",
                        choices=["Container", "In ground"],
                        value="Container",
                    )
                    size_label = gr.Radio(
                        label="Visible size",
                        choices=["Small", "Medium", "Large"],
                        value="Medium",
                    )
                    manual_interval = gr.Textbox(
                        label="Custom watering interval (optional)",
                        info=(
                            "Leave blank to use plant care data. A value here replaces "
                            "that base interval; weather can still shift dates."
                        ),
                        placeholder="Example: 7",
                        value="",
                        max_lines=1,
                    )
                preview_button = gr.Button("Preview watering dates")
                care_summary = gr.Markdown(elem_classes="wl-section")
                schedule = gr.Dataframe(
                    headers=["Date", "Reason", "Confidence"],
                    datatype=["str", "str", "str"],
                    label="30-day watering dates",
                    interactive=True,
                    wrap=True,
                )
                save_button = gr.Button("Save plant", variant="primary")
                save_status = gr.Markdown(elem_classes="wl-status")

        demo.load(
            load_dashboard,
            inputs=None,
            outputs=[garden, delete_choice],
            api_visibility="private",
        )
        analyze_button.click(
            analyze_photos,
            inputs=[image_1, image_2, image_3, guest_used_state],
            outputs=[
                result_state,
                candidates,
                visual_summary,
                planting,
                size_label,
                guest_used_state,
            ],
            api_visibility="private",
            concurrency_limit=1,
        )
        species_search.input(
            search_species,
            inputs=species_search,
            outputs=species_override,
            api_visibility="private",
            trigger_mode="always_last",
        )
        preview_button.click(
            preview,
            inputs=[
                candidates,
                species_override,
                result_state,
                location,
                planting,
                size_label,
                manual_interval,
            ],
            outputs=[plan_state, schedule, care_summary],
            api_visibility="private",
        )
        save_button.click(
            save,
            inputs=[
                image_1,
                nickname,
                preferred_time,
                candidates,
                species_override,
                result_state,
                plan_state,
                schedule,
            ],
            outputs=[save_status, garden, delete_choice],
            api_visibility="private",
        )
        export_button.click(
            export,
            inputs=None,
            outputs=[calendar_file, export_status],
            api_visibility="private",
        )
        delete_button.click(
            delete,
            inputs=delete_choice,
            outputs=[garden, delete_choice, delete_status],
            api_visibility="private",
        )
    return demo


def _garden_html(application: WaterleafApplication, owner: str | None) -> str:
    if not owner:
        return (
            '<div class="wl-empty">Sign in to save plants and export one garden calendar.</div>'
        )
    plants = application.store.list_plants(owner)
    if not plants:
        return '<div class="wl-empty">No saved plants.</div>'
    cards = []
    for plant in plants:
        schedule = application.store.get_schedule(owner, plant.id)
        next_date = schedule[0]["date"] if schedule else "Not scheduled"
        image_url = f"{application.public_base_url}/media/{plant.image_id}.jpg"
        profile_url = f"{application.public_base_url}/plants/{plant.public_slug}"
        cards.append(
            f"""
            <article class="wl-plant">
              <img src="{html.escape(image_url)}" alt="{html.escape(plant.nickname)}">
              <div class="wl-plant-body">
                <h3>
                  <a href="{html.escape(profile_url)}" target="_blank">
                    {html.escape(plant.nickname)}
                  </a>
                </h3>
                <p>{html.escape(plant.common_name)}</p>
                <p>Next: {html.escape(next_date)}</p>
              </div>
            </article>
            """
        )
    return '<div class="wl-garden">' + "".join(cards) + "</div>"


def _plant_delete_choices(application: WaterleafApplication, owner: str | None):
    plants = application.store.list_plants(owner) if owner else []
    choices = [(plant.nickname, plant.id) for plant in plants]
    return gr.Dropdown(choices=choices, value=None)


def _candidate_label(candidate: TaxonCandidate) -> str:
    score = f"{candidate.confidence:.0%}" if candidate.confidence else "database match"
    if candidate.common_name.casefold() == candidate.scientific_name.casefold():
        return f"{candidate.scientific_name} | Common name unavailable | {score}"
    return f"{candidate.common_name} | {candidate.scientific_name} | {score}"


def _selected_candidate(
    candidate_key: str | None,
    override_json: str | None,
    result_json: str,
) -> TaxonCandidate:
    if override_json:
        return TaxonCandidate.model_validate_json(override_json)
    if not result_json or not candidate_key:
        raise gr.Error("Confirm a species before scheduling.")
    result = IdentificationResult.model_validate_json(result_json)
    for candidate in result.candidates:
        if candidate.taxon_key == candidate_key:
            return candidate
    raise gr.Error("The selected species is no longer available.")


def _plan_to_json(plan: SchedulePlan) -> str:
    return json.dumps(
        {
            "location": plan.location.model_dump(),
            "care": plan.care.model_dump(),
            "events": [
                {
                    "date": item.date.isoformat(),
                    "reason": item.reason,
                    "confidence": item.confidence,
                }
                for item in plan.events
            ],
            "is_container": plan.is_container,
            "size_label": plan.size_label,
        }
    )


def _plan_from_json(payload: str) -> SchedulePlan:
    if not payload:
        raise gr.Error("Preview the schedule before saving.")
    data = json.loads(payload)
    return SchedulePlan(
        location=LocationMatch.model_validate(data["location"]),
        care=CareProfile.model_validate(data["care"]),
        events=[
            WateringEvent(
                date=date.fromisoformat(item["date"]),
                reason=item["reason"],
                confidence=item["confidence"],
            )
            for item in data["events"]
        ],
        is_container=data["is_container"],
        size_label=data["size_label"],
    )


def _events_from_rows(rows) -> list[WateringEvent]:
    if hasattr(rows, "values"):
        rows = rows.values.tolist()
    events = []
    for row in rows or []:
        if not row or not row[0]:
            continue
        events.append(
            WateringEvent(
                date=date.fromisoformat(str(row[0])),
                reason=str(row[1]),
                confidence=str(row[2]),
            )
        )
    return events


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value.strip())
    except ValueError as exc:
        raise gr.Error("Use a watering time such as 07:30.") from exc


def _parse_optional_interval(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        interval = int(text)
    except ValueError as exc:
        raise ValueError(
            "Enter a whole number from 1 to 30, or leave it blank."
        ) from exc
    if not 1 <= interval <= 30:
        raise ValueError("Enter a whole number from 1 to 30, or leave it blank.")
    return interval


def _care_markdown(care: CareProfile, location: LocationMatch) -> str:
    interval = (
        f"{care.min_days}-{care.max_days} days"
        if care.min_days and care.max_days
        else "manual interval required"
    )
    sun = ", ".join(care.sunlight) if care.sunlight else "not available"
    return (
        f"**{care.common_name}**  \n"
        f"Care baseline: {interval} · Sun: {sun} · Timezone: {location.timezone}"
    )
