from __future__ import annotations

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=200)
    code_project_path: str | None = None
    branding: dict | None = None


class TenantOut(BaseModel):
    id: str
    slug: str
    name: str
    status: str
    code_project_path: str | None = None
    branding: dict = Field(default_factory=dict)

    @classmethod
    def from_orm(cls, t) -> TenantOut:
        return cls(
            id=str(t.id),
            slug=t.slug,
            name=t.name,
            status=t.status,
            code_project_path=t.code_project_path,
            branding=t.branding_json or {},
        )


class TenantAdminCreate(BaseModel):
    username: str = Field(min_length=2, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="owner", pattern=r"^(owner|admin)$")


class TenantAdminOut(BaseModel):
    id: str
    tenant_id: str
    username: str
    role: str


class TenantLoginRequest(BaseModel):
    username: str
    password: str


class TenantLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant: TenantOut
    admin: TenantAdminOut


class TenantMeResponse(BaseModel):
    tenant: TenantOut
    admin: TenantAdminOut
