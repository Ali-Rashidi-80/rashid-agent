"""Metis URL resolution tests.

Verified against the live Metis API: wrapper bases (e.g. .../api/v1/wrapper/grok)
serve chat completions at <base>/chat/completions. The /openai/v1 gateway rejects
wrapper keys/models with 404 model_not_found, so it must never be the default.
"""

from app.config.settings import Settings
from app.services.metis import METIS_DEFAULT_OPENAI_URL, resolve_metis_chat_url


def test_wrapper_grok_base_resolves_to_wrapper_chat_completions():
    settings = Settings(metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok")
    url = resolve_metis_chat_url(settings)
    assert url == "https://api.metisai.ir/api/v1/wrapper/grok/chat/completions"
    assert "/api/v1/openai" not in url


def test_explicit_openai_url_override():
    settings = Settings(
        metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok",
        metis_openai_url="https://custom.example/openai/v1/chat/completions",
    )
    assert resolve_metis_chat_url(settings) == "https://custom.example/openai/v1/chat/completions"


def test_full_chat_completions_base_unchanged():
    url = "https://api.metisai.ir/openai/v1/chat/completions"
    settings = Settings(metis_base_url=url, metis_openai_url="")
    assert resolve_metis_chat_url(settings) == url


def test_empty_base_falls_back_to_default():
    settings = Settings(metis_base_url="", metis_openai_url="")
    assert resolve_metis_chat_url(settings) == METIS_DEFAULT_OPENAI_URL
