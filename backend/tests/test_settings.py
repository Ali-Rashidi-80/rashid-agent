"""Settings tests."""

from app.config.settings import Settings


def test_effective_arq_redis_url_defaults_to_db1():
    settings = Settings(redis_url="redis://127.0.0.1:6380/0", arq_redis_url="")
    assert settings.effective_arq_redis_url == "redis://127.0.0.1:6380/1"


def test_effective_arq_redis_url_explicit_override():
    settings = Settings(
        redis_url="redis://127.0.0.1:6380/0",
        arq_redis_url="redis://127.0.0.1:6380/2",
    )
    assert settings.effective_arq_redis_url == "redis://127.0.0.1:6380/2"
