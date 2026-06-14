from __future__ import annotations

import os

OAUTH_VARIABLES = (
    "OAUTH_CLIENT_ID",
    "OAUTH_CLIENT_SECRET",
    "OAUTH_SCOPES",
    "OPENID_PROVIDER_URL",
)


def is_hf_space() -> bool:
    return bool(os.getenv("SPACE_ID") or os.getenv("SPACE_HOST"))


def has_hf_oauth() -> bool:
    return all(os.getenv(name) for name in OAUTH_VARIABLES)


def configure_hf_space_environment() -> None:
    if not is_hf_space() or not has_hf_oauth():
        return
    space_id = os.getenv("SPACE_ID") or os.environ["SPACE_HOST"]
    os.environ.setdefault("SYSTEM", "spaces")
    os.environ.setdefault("SPACE_ID", space_id)
