from waterleaf.runtime import build_application
from waterleaf.services.demo import DemoTaxonomy
from waterleaf.settings import Settings


def test_settings_derive_public_url_from_space_host(monkeypatch, tmp_path):
    monkeypatch.setenv("SPACE_HOST", "hkaraoguz-waterleaf.hf.space")
    monkeypatch.setenv("WATERLEAF_DATA_DIR", str(tmp_path))

    settings = Settings.from_env()

    assert settings.public_base_url == "https://hkaraoguz-waterleaf.hf.space"
    assert settings.database_path == tmp_path / "waterleaf.sqlite3"


def test_runtime_uses_demo_identification_without_modal_endpoint(tmp_path):
    settings = Settings(
        data_directory=tmp_path,
        public_base_url="http://localhost:7860",
        perenual_api_key=None,
        modal_endpoint=None,
        modal_key=None,
        modal_secret=None,
    )

    application = build_application(settings)

    assert application.identification is not None
    assert isinstance(application.taxonomy, DemoTaxonomy)
