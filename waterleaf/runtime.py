from __future__ import annotations

from waterleaf.application import WaterleafApplication
from waterleaf.services.care import LocalCareCatalog
from waterleaf.services.demo import DemoTaxonomy, build_demo_identification
from waterleaf.services.gbif import GbifClient
from waterleaf.services.identification import IdentificationService
from waterleaf.services.llama_cpp import LlamaCppClient
from waterleaf.services.open_meteo import OpenMeteoClient
from waterleaf.settings import Settings
from waterleaf.storage import GardenStore


def build_application(settings: Settings | None = None) -> WaterleafApplication:
    settings = settings or Settings.from_env()
    settings.data_directory.mkdir(parents=True, exist_ok=True)

    if settings.modal_endpoint:
        taxonomy = GbifClient()
        identification = IdentificationService(
            vision=LlamaCppClient(
                endpoint=settings.modal_endpoint,
                modal_key=settings.modal_key,
                modal_secret=settings.modal_secret,
            ),
            taxonomy=taxonomy,
        )
    else:
        taxonomy = DemoTaxonomy()
        identification = build_demo_identification()

    return WaterleafApplication(
        store=GardenStore(settings.database_path),
        media_directory=settings.media_directory,
        export_directory=settings.export_directory,
        public_base_url=settings.public_base_url,
        care=LocalCareCatalog(),
        weather=OpenMeteoClient(),
        identification=identification,
        taxonomy=taxonomy,
    )
