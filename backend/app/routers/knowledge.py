"""Knowledge base CRUD + document upload (Phase B3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tenant_admin import require_tenant_admin
from app.config.settings import Settings, get_settings
from app.db.models.tenant import TenantAdmin
from app.db.repositories.knowledge import KnowledgeRepository
from app.db.session import get_db_session
from app.schemas.knowledge import (
    ErpRagSyncOut,
    ErpRagSyncRequest,
    KbDocumentOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
)
from app.services.erp_rag_client import ErpRagError
from app.services.erp_rag_sync import ErpRagSyncService
from app.services.kb_ingest import KbIngestService
from app.services.kb_storage import KbStorageService

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])


def _kb_out(kb, document_count: int = 0) -> KnowledgeBaseOut:
    return KnowledgeBaseOut(
        id=kb.id,
        tenant_id=kb.tenant_id,
        name=kb.name,
        system_prompt=kb.system_prompt,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        document_count=document_count,
    )


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_knowledge_bases(
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    rows = await repo.list_bases(admin.tenant_id)
    return [_kb_out(kb, count) for kb, count in rows]


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    kb = await repo.create_base(admin.tenant_id, name=body.name, system_prompt=body.system_prompt)
    return _kb_out(kb, 0)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    kb = await repo.get_base(admin.tenant_id, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    docs = await repo.list_documents(admin.tenant_id, kb_id)
    return _kb_out(kb, len(docs))


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    kb = await repo.update_base(
        admin.tenant_id,
        kb_id,
        name=body.name,
        system_prompt=body.system_prompt,
    )
    if kb is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    docs = await repo.list_documents(admin.tenant_id, kb_id)
    return _kb_out(kb, len(docs))


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = KnowledgeRepository(db)
    storage = KbStorageService(settings)
    ok = await repo.delete_base(admin.tenant_id, kb_id, storage)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})


@router.get("/{kb_id}/documents", response_model=list[KbDocumentOut])
async def list_documents(
    kb_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    if await repo.get_base(admin.tenant_id, kb_id) is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    return await repo.list_documents(admin.tenant_id, kb_id)


@router.post(
    "/{kb_id}/documents",
    response_model=list[KbDocumentOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_documents(
    kb_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = KnowledgeRepository(db)
    if await repo.get_base(admin.tenant_id, kb_id) is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    if not files:
        raise HTTPException(status_code=400, detail={"error": {"code": "no_files"}})

    storage = KbStorageService(settings)
    max_bytes = max(1, int(settings.kb_max_upload_bytes or 25 * 1024 * 1024))
    created: list[KbDocumentOut] = []
    for upload in files:
        data = await upload.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": {
                        "code": "file_too_large",
                        "message": f"max_upload_bytes={max_bytes}",
                    }
                },
            )
        filename = upload.filename or "document.txt"
        doc_id = uuid.uuid4()
        path = storage.save_bytes(
            tenant_id=admin.tenant_id,
            kb_id=kb_id,
            doc_id=doc_id,
            filename=filename,
            data=data,
        )
        doc = await repo.create_document(
            admin.tenant_id,
            kb_id,
            filename=filename,
            mime=upload.content_type or "application/octet-stream",
            size=len(data),
            storage_path=str(path),
            doc_id=doc_id,
        )

        # Heavy uploads go to ARQ; small docs ingest inline for snappy UX/tests.
        enqueued = False
        arq_min = max(1, int(settings.kb_arq_ingest_min_bytes or 1_000_000))
        if len(data) >= arq_min:
            try:
                from arq import create_pool
                from arq.connections import RedisSettings

                pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
                try:
                    job = await pool.enqueue_job(
                        "job_kb_ingest",
                        str(doc.id),
                        str(admin.tenant_id),
                    )
                    enqueued = job is not None
                finally:
                    await pool.aclose()  # type: ignore[attr-defined]
            except Exception:
                enqueued = False

        if enqueued:
            created.append(KbDocumentOut.model_validate(doc))
            continue

        ingest = KbIngestService(db, settings)
        ingest_doc_id = doc_id
        try:
            doc = await ingest.ingest_document(ingest_doc_id, admin.tenant_id)
        except Exception:
            refreshed = await repo.get_document(admin.tenant_id, kb_id, ingest_doc_id)
            if refreshed:
                doc = refreshed

        created.append(KbDocumentOut.model_validate(doc))
    return created


@router.get("/{kb_id}/documents/{doc_id}", response_model=KbDocumentOut)
async def get_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
):
    repo = KnowledgeRepository(db)
    doc = await repo.get_document(admin.tenant_id, kb_id, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "doc_not_found"}})
    return doc


@router.put("/{kb_id}/documents/{doc_id}", response_model=KbDocumentOut)
async def replace_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = KnowledgeRepository(db)
    doc = await repo.get_document(admin.tenant_id, kb_id, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "doc_not_found"}})
    storage = KbStorageService(settings)
    data = await file.read()
    max_bytes = max(1, int(settings.kb_max_upload_bytes or 25 * 1024 * 1024))
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "file_too_large",
                    "message": f"max_upload_bytes={max_bytes}",
                }
            },
        )
    filename = file.filename or doc.filename
    path = storage.save_bytes(
        tenant_id=admin.tenant_id,
        kb_id=kb_id,
        doc_id=doc_id,
        filename=filename,
        data=data,
    )
    doc.filename = filename
    doc.mime = file.content_type or doc.mime
    doc.size = len(data)
    doc.storage_path = str(path)
    doc.status = "pending"
    doc.error_message = None
    await db.commit()
    ingest = KbIngestService(db, settings)
    try:
        doc = await ingest.ingest_document(doc_id, admin.tenant_id)
    except Exception:
        refreshed = await repo.get_document(admin.tenant_id, kb_id, doc_id)
        if refreshed:
            doc = refreshed
    return doc


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = KnowledgeRepository(db)
    storage = KbStorageService(settings)
    ok = await repo.delete_document(admin.tenant_id, kb_id, doc_id, storage)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": {"code": "doc_not_found"}})


@router.post("/{kb_id}/reindex", response_model=list[KbDocumentOut])
async def reindex_knowledge_base(
    kb_id: uuid.UUID,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = KnowledgeRepository(db)
    if await repo.get_base(admin.tenant_id, kb_id) is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "kb_not_found"}})
    docs = await repo.list_documents(admin.tenant_id, kb_id)
    ingest = KbIngestService(db, settings)
    out: list[KbDocumentOut] = []
    for doc in docs:
        try:
            updated = await ingest.ingest_document(doc.id, admin.tenant_id)
            out.append(KbDocumentOut.model_validate(updated))
        except Exception:
            refreshed = await repo.get_document(admin.tenant_id, kb_id, doc.id)
            if refreshed:
                out.append(KbDocumentOut.model_validate(refreshed))
    return out


@router.post("/{kb_id}/erp-sync", response_model=ErpRagSyncOut)
async def sync_knowledge_base_from_erp(
    kb_id: uuid.UUID,
    body: ErpRagSyncRequest,
    admin: TenantAdmin = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    """Phase E: pull ERP RAG chunks (staff JWT) into this tenant KB."""
    service = ErpRagSyncService(db, settings)
    try:
        result = await service.sync(
            tenant_id=admin.tenant_id,
            kb_id=kb_id,
            queries=body.queries,
            collections=body.collections,
            limit=body.limit,
            access_token=body.access_token,
        )
    except ErpRagError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return ErpRagSyncOut(
        chunks_fetched=result.chunks_fetched,
        documents_created=result.documents_created,
        documents_updated=result.documents_updated,
        documents=[KbDocumentOut.model_validate(d) for d in result.documents],
    )
