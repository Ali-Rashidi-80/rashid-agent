"""Org bot API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrgBotCreate(BaseModel):
    kb_id: uuid.UUID
    title: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]+$")
    auth_mode: str = "password"
    password: str | None = None
    single_session: bool = False
    rate_limit_per_min: int = 30


class OrgBotOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    kb_id: uuid.UUID
    title: str
    slug: str
    auth_mode: str
    single_session: bool
    rate_limit_per_min: int
    active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrgBotOtpIssue(BaseModel):
    label: str = ""
    ttl_minutes: int = 30


class OrgBotOtpIssued(BaseModel):
    credential_id: uuid.UUID
    otp: str
    expires_at: datetime | None = None


class OrgBotPasswordIssue(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    label: str = ""


class PublicBotInfo(BaseModel):
    slug: str
    title: str
    auth_mode: str
    active: bool


class PublicBotLoginRequest(BaseModel):
    secret: str = Field(min_length=1, max_length=128)
    username: str | None = None


class PublicBotLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    bot: OrgBotOut


class PublicBotChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    provider: str | None = None


class OrgBotPhoneCreate(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    label: str = ""


class OrgBotPhoneOut(BaseModel):
    id: uuid.UUID
    bot_id: uuid.UUID
    phone: str
    label: str
    active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublicBotOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class PublicBotOtpRequestResponse(BaseModel):
    ok: bool = True
    message: str = "اگر شماره مجاز باشد، کد یک‌بارمصرف ارسال می‌شود."
