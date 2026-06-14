from __future__ import annotations

import html
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from waterleaf.application import WaterleafApplication

IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")


def create_web_app(
    application: WaterleafApplication,
    *,
    mount_ui: bool = True,
) -> FastAPI:
    app = FastAPI(title="Waterleaf", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/plants/{public_slug}", response_class=HTMLResponse)
    def public_plant(public_slug: str) -> str:
        plant = application.store.get_public_plant(public_slug)
        if plant is None:
            raise HTTPException(status_code=404, detail="Plant not found")
        context = "Container plant" if plant.is_container else "In-ground plant"
        schedule = application.store.get_public_schedule(public_slug)
        return _public_profile_html(
            nickname=plant.nickname,
            common_name=plant.common_name,
            scientific_name=plant.scientific_name,
            context=f"{context}, {plant.size_label}",
            care_min_days=plant.care_min_days,
            care_max_days=plant.care_max_days,
            schedule=schedule,
            image_url=f"/media/{plant.image_id}.jpg",
        )

    @app.get("/media/{image_name}")
    def media(image_name: str) -> FileResponse:
        if not IMAGE_NAME.fullmatch(image_name):
            raise HTTPException(status_code=404, detail="Image not found")
        path = application.media_directory / image_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(path, media_type="image/jpeg")

    if mount_ui:
        import gradio as gr

        from waterleaf.ui import CSS, build_ui

        app = gr.mount_gradio_app(
            app,
            build_ui(application),
            path="/",
            allowed_paths=[
                str(application.media_directory.resolve()),
                str(application.export_directory.resolve()),
            ],
            max_file_size="12mb",
            show_error=True,
            footer_links=[],
            theme=gr.themes.Base(),
            css=CSS,
        )
    return app


def _public_profile_html(
    *,
    nickname: str,
    common_name: str,
    scientific_name: str,
    context: str,
    care_min_days: int | None,
    care_max_days: int | None,
    schedule: list[dict[str, object]],
    image_url: str,
) -> str:
    if care_min_days is None or care_max_days is None:
        care_cadence = "Care cadence unavailable"
    elif care_min_days == care_max_days:
        care_cadence = f"Every {care_min_days} days"
    else:
        care_cadence = f"Every {care_min_days}-{care_max_days} days"
    schedule_items = "".join(
        "<li>"
        f"<time>{html.escape(str(item.get('date', '')))}</time>"
        f"<span>{html.escape(str(item.get('reason', 'Scheduled watering')))}</span>"
        "</li>"
        for item in schedule
    )
    if not schedule_items:
        schedule_items = "<li><span>No upcoming watering dates.</span></li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(nickname)} | Waterleaf</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f7f2; color: #172018; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 28px 18px 48px; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}
    .brand {{ font-weight: 760; font-size: 20px; }}
    img {{ width: 100%; max-height: 62vh; object-fit: cover; border-radius: 8px; display: block; }}
    h1 {{ font-size: clamp(30px, 7vw, 52px); margin: 22px 0 4px; letter-spacing: 0; }}
    .latin {{ color: #526157; font-style: italic; font-size: 18px; }}
    .facts {{ border-top: 1px solid #cad4c8; margin-top: 22px; padding-top: 18px; }}
    h2 {{ font-size: 20px; margin: 28px 0 10px; }}
    ul {{ list-style: none; margin: 0; padding: 0; border-top: 1px solid #cad4c8; }}
    li {{
      display: grid;
      grid-template-columns: minmax(100px, 130px) 1fr;
      gap: 16px;
      padding: 13px 0;
      border-bottom: 1px solid #cad4c8;
    }}
    time {{ font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <header><div class="brand">Waterleaf</div><div>Plant profile</div></header>
    <img src="{html.escape(image_url)}" alt="{html.escape(nickname)}">
    <h1>{html.escape(nickname)}</h1>
    <div>{html.escape(common_name)}</div>
    <div class="latin">{html.escape(scientific_name)}</div>
    <div class="facts">
      <div>{html.escape(context)}</div>
      <div>{html.escape(care_cadence)}</div>
    </div>
    <h2>Upcoming watering</h2>
    <ul>{schedule_items}</ul>
  </main>
</body>
</html>"""
