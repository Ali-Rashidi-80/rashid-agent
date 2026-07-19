from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root .env must load regardless of CWD (uvicorn is often started from
# backend/). Later entries win, so a CWD-local .env still takes precedence.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://rashid:rashid@127.0.0.1:5432/rashid"
    redis_url: str = "redis://127.0.0.1:6380/0"
    arq_redis_url: str = ""
    rashid_host: str = "127.0.0.1"
    rashid_port: int = 8000
    openai_api_key: str = ""
    metis_api_key: str = ""
    metis_base_url: str = "https://api.metisai.ir/api/v1/wrapper/grok"
    metis_openai_url: str = ""
    rashid_model: str = "grok-code-fast-1"
    rashid_debug: bool = False
    rashid_token: str = ""
    allow_blind_apply: bool = False
    # Override for the data dir holding project_path.txt (also disables the
    # legacy config.txt fallback). Used for test isolation.
    rashid_data_dir: str = ""

    @property
    def api_key(self) -> str:
        return self.metis_api_key or self.openai_api_key

    @property
    def effective_arq_redis_url(self) -> str:
        if self.arq_redis_url:
            return self.arq_redis_url
        if self.redis_url.rstrip("/").endswith("/0"):
            return f"{self.redis_url.rsplit('/', 1)[0]}/1"
        return f"{self.redis_url.rstrip('/')}/1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
