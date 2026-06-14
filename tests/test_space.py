import os

from waterleaf.space import (
    OAUTH_VARIABLES,
    configure_hf_space_environment,
    has_hf_oauth,
    is_hf_space,
)


def _clear_space_environment(monkeypatch):
    for name in (*OAUTH_VARIABLES, "SPACE_ID", "SPACE_HOST", "SYSTEM"):
        monkeypatch.delenv(name, raising=False)


def test_local_environment_does_not_enable_space_oauth(monkeypatch):
    _clear_space_environment(monkeypatch)

    configure_hf_space_environment()

    assert not is_hf_space()
    assert not has_hf_oauth()


def test_complete_oauth_environment_configures_gradio_space(monkeypatch):
    _clear_space_environment(monkeypatch)
    monkeypatch.setenv("SPACE_HOST", "build-small-hackathon-waterleaf.hf.space")
    for name in OAUTH_VARIABLES:
        monkeypatch.setenv(name, f"test-{name.casefold()}")

    configure_hf_space_environment()

    assert is_hf_space()
    assert has_hf_oauth()
    assert os.environ["SYSTEM"] == "spaces"
    assert os.environ["SPACE_ID"] == "build-small-hackathon-waterleaf.hf.space"


def test_incomplete_oauth_environment_is_not_enabled(monkeypatch):
    _clear_space_environment(monkeypatch)
    monkeypatch.setenv("SPACE_HOST", "build-small-hackathon-waterleaf.hf.space")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "client")

    configure_hf_space_environment()

    assert is_hf_space()
    assert not has_hf_oauth()
    assert os.environ.get("SYSTEM") is None
