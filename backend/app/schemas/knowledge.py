"""Knowledge base API schemas (Phase B3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    system_prompt: str = ""


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    system_prompt: str | None = None


class KnowledgeBaseOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    system_prompt: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    document_count: int = 0

    model_config = {"from_attributes": True}


class KbDocumentOut(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    mime: str
    size: int
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ErpRagSyncRequest(BaseModel):
    """Pull chunks from Liquidglass ERP RAG into this knowledge base."""

    queries: list[str] = Field(min_length=1, max_length=20)
    collections: list[str] | None = None
    limit: int = Field(default=8, ge=1, le=50)
    access_token: str | None = None


class ErpRagSyncOut(BaseModel):
    chunks_fetched: int
    documents_created: int
    documents_updated: int
    documents: list[KbDocumentOut]
