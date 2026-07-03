"""Metis URL resolution tests."""

from app.config.settings import Settings
from app.services.metis import METIS_DEFAULT_OPENAI_URL, resolve_metis_chat_url


def test_wrapper_grok_url_resolves_to_openai_endpoint():
    settings = Settings(metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok")
    assert resolve_metis_chat_url(settings) == METIS_DEFAULT_OPENAI_URL
    assert "/api/v1/openai" not in resolve_metis_chat_url(settings)


def test_explicit_openai_url_override():
    settings = Settings(
        metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok",
        metis_openai_url="https://custom.example/openai/v1/chat/completions",
    )
    assert resolve_metis_chat_url(settings) == "https://custom.example/openai/v1/chat/completions"


def test_already_openai_url_unchanged():
    url = "https://api.metisai.ir/openai/v1/chat/completions"
    settings = Settings(metis_openai_url=url)
    assert resolve_metis_chat_url(settings) == url
