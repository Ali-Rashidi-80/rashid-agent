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
    rashid_provider: str = "grok"
    rashid_debug: bool = False
    rashid_token: str = ""
    allow_blind_apply: bool = False
    # Override for the data dir holding project_path.txt (also disables the
    # legacy config.txt fallback). Used for test isolation.
    rashid_data_dir: str = ""

    # Phase T0 — optional seed admin for first tenant (adl-omid)
    tenant_seed_admin_user: str = ""
    tenant_seed_admin_password: str = ""
    tenant_seed_code_project_path: str = r"D:\0\Liquidglasslegalerp"

    # Phase B — knowledge base / RAG
    kb_embedding_model: str = "text-embedding-3-small"
    kb_chunk_size: int = 800
    kb_chunk_overlap: int = 120
    kb_top_k: int = 6
    kb_storage_dir: str = ""
    kb_max_upload_bytes: int = 25 * 1024 * 1024
    # When true, Metis embed failures fall back to HashEmbedder (tests only).
    kb_embed_hash_fallback: bool = False
    kb_ocr_vision_model: str = "gpt-4o-mini"
    # Files at/above this size enqueue ARQ job_kb_ingest (else inline).
    kb_arq_ingest_min_bytes: int = 1_000_000

    # Phase D — messenger
    secrets_encryption_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_org_bot_slug: str = ""
    telegram_api_base: str = "https://api.telegram.org"
    bale_api_base: str = "https://tapi.bale.ai"

    # SMS OTP (MeliPayamak console — Liquidglass pattern 477732)
    sms_console_api_token: str = ""
    melipayamak_console_token: str = ""  # alias for SMS_CONSOLE_API_TOKEN
    sms_otp_pattern_body_id: int = 477732
    sms_otp_pattern_arg_slots: str = "code,minutes"
    sms_otp_ttl_minutes: int = 2
    sms_delivery_enabled: bool = True
    sms_provider_mode: str = "stub"  # stub | real
    sms_provider_timeout_seconds: float = 30.0

    # Phase E — optional Liquidglass ERP RAG → Rashid KB bridge
    erp_rag_base_url: str = ""
    erp_rag_username: str = ""
    erp_rag_password: str = ""

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
