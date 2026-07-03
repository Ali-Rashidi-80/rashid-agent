from pydantic import BaseModel


class HealthComponent(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    postgres: HealthComponent
    redis: HealthComponent
    worker: HealthComponent
