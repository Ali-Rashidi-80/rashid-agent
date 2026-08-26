"""Knowledge base persistence with tenant RLS scoping."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KbChunk, KbDocument, KnowledgeBase
from app.db.tenant_context import set_tenant_id
from app.services.kb_storage import KbStorageService


class KnowledgeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _scope(self, tenant_id: uuid.UUID) -> None:
        await set_tenant_id(self.db, tenant_id)

    async def list_bases(self, tenant_id: uuid.UUID) -> list[tuple[KnowledgeBase, int]]:
        await self._scope(tenant_id)
        count_sq = (
            select(KbDocument.kb_id, func.count(KbDocument.id).label("cnt"))
            .where(KbDocument.tenant_id == tenant_id)
            .group_by(KbDocument.kb_id)
            .subquery()
        )
        result = await self.db.execute(
            select(KnowledgeBase, func.coalesce(count_sq.c.cnt, 0))
            .outerjoin(count_sq, count_sq.c.kb_id == KnowledgeBase.id)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .order_by(KnowledgeBase.created_at.asc())
        )
        return [(row[0], int(row[1])) for row in result.all()]

    async def get_base(self, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> KnowledgeBase | None:
        await self._scope(tenant_id)
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_base(
        self, tenant_id: uuid.UUID, *, name: str, system_prompt: str = ""
    ) -> KnowledgeBase:
        await self._scope(tenant_id)
        kb = KnowledgeBase(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name.strip(),
            system_prompt=system_prompt or "",
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def update_base(
        self,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        *,
        name: str | None = None,
        system_prompt: str | None = None,
    ) -> KnowledgeBase | None:
        kb = await self.get_base(tenant_id, kb_id)
        if kb is None:
            return None
        if name is not None:
            kb.name = name.strip()
        if system_prompt is not None:
            kb.system_prompt = system_prompt
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def delete_base(
        self, tenant_id: uuid.UUID, kb_id: uuid.UUID, storage: KbStorageService
    ) -> bool:
        kb = await self.get_base(tenant_id, kb_id)
        if kb is None:
            return False
        docs = await self.list_documents(tenant_id, kb_id)
        for doc in docs:
            await self.delete_document(tenant_id, kb_id, doc.id, storage)
        await self._scope(tenant_id)
        await self.db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        await self.db.commit()
        return True

    async def list_documents(self, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> list[KbDocument]:
        await self._scope(tenant_id)
        result = await self.db.execute(
            select(KbDocument)
            .where(KbDocument.kb_id == kb_id, KbDocument.tenant_id == tenant_id)
            .order_by(KbDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(
        self, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID
    ) -> KbDocument | None:
        await self._scope(tenant_id)
        result = await self.db.execute(
            select(KbDocument).where(
                KbDocument.id == doc_id,
                KbDocument.kb_id == kb_id,
                KbDocument.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_document(
        self,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        *,
        filename: str,
        mime: str,
        size: int,
        storage_path: str,
        doc_id: uuid.UUID | None = None,
    ) -> KbDocument:
        await self._scope(tenant_id)
        doc = KbDocument(
            id=doc_id or uuid.uuid4(),
            kb_id=kb_id,
            tenant_id=tenant_id,
            filename=filename,
            mime=mime or "application/octet-stream",
            size=size,
            status="pending",
            storage_path=storage_path,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete_document(
        self,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        doc_id: uuid.UUID,
        storage: KbStorageService,
    ) -> bool:
        """Atomically remove chunks + DB row + on-disk file."""
        doc = await self.get_document(tenant_id, kb_id, doc_id)
        if doc is None:
            return False
        path = Path(doc.storage_path) if doc.storage_path else None
        await self._scope(tenant_id)
        await self.db.execute(delete(KbChunk).where(KbChunk.doc_id == doc_id))
        await self.db.execute(delete(KbDocument).where(KbDocument.id == doc_id))
        await self.db.commit()
        try:
            storage.delete_doc_dir(tenant_id, kb_id, doc_id)
        except OSError:
            pass
        if path and path.exists():
            path.unlink(missing_ok=True)
        return True
