"""Metis URL resolution tests.

Verified against the live Metis API: wrapper bases (e.g. .../api/v1/wrapper/grok)
serve chat completions at <base>/chat/completions. The /openai/v1 gateway rejects
wrapper keys/models with 404 model_not_found, so it must never be the default.
"""

from app.config.settings import Settings
from app.services.metis import (
    METIS_DEFAULT_OPENAI_URL,
    is_chat_model_id,
    metis_wrapper_path,
    normalize_provider,
    resolve_metis_chat_url,
    resolve_metis_models_url,
)


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


def test_models_url_derived_from_wrapper_chat_url():
    settings = Settings(metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok")
    assert resolve_metis_models_url(settings) == "https://api.metisai.ir/api/v1/wrapper/grok/models"


def test_provider_arg_builds_wrapper_url_independent_of_base():
    settings = Settings(metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok")
    assert (
        resolve_metis_chat_url(settings, provider="anthropic")
        == "https://api.metisai.ir/api/v1/wrapper/anthropic/chat/completions"
    )
    # OpenAI chat must use openai_chat_completion (live Metis pricing path).
    assert (
        resolve_metis_chat_url(settings, provider="openai")
        == "https://api.metisai.ir/api/v1/wrapper/openai_chat_completion/chat/completions"
    )
    assert (
        resolve_metis_models_url(settings, provider="openai")
        == "https://api.metisai.ir/api/v1/wrapper/openai_chat_completion/models"
    )
    assert metis_wrapper_path("openai") == "openai_chat_completion"
    assert metis_wrapper_path("grok") == "grok"


def test_normalize_provider_dedupes_openai_aliases():
    assert normalize_provider("openai_chat_completion") == "openai"
    assert normalize_provider("GROK") == "grok"
    assert normalize_provider("unknown") == ""


def test_filters_non_chat_model_ids():
    assert is_chat_model_id("gpt-4o")
    assert not is_chat_model_id("text-embedding-3-small")
    assert not is_chat_model_id("whisper-1")


def test_metis_service_provider_selects_wrapper_url():
    from app.services.metis import MetisService

    settings = Settings(metis_base_url="https://api.metisai.ir/api/v1/wrapper/grok")
    svc = MetisService(settings, model="gpt-4o-mini", provider="openai")
    assert svc.provider == "openai"
    assert (
        svc._chat_url()
        == "https://api.metisai.ir/api/v1/wrapper/openai_chat_completion/chat/completions"
    )


def test_anthropic_payload_omits_deprecated_temperature():
    from app.services.metis import MetisService

    settings = Settings()
    anth = MetisService(settings, model="claude-sonnet-5", provider="anthropic")
    payload = anth._base_chat_payload(
        [{"role": "user", "content": "hi"}],
        stream=True,
    )
    assert "temperature" not in payload
    assert payload.get("max_tokens") == 4096

    openai = MetisService(settings, model="gpt-4o-mini", provider="openai")
    openai_payload = openai._base_chat_payload(
        [{"role": "user", "content": "hi"}],
        stream=True,
    )
    assert openai_payload.get("temperature") == 0.3
