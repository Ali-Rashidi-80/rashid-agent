
from app.config.settings import Settings, get_settings
from app.db.session import get_db_session
from app.services.project_path import ProjectPathService
from app.services.redis_client import get_redis

__all__ = [
    "Settings",
    "get_settings",
    "get_db_session",
    "get_redis",
    "get_project_path_service",
]


def get_project_path_service() -> ProjectPathService:
    return ProjectPathService(get_settings())
