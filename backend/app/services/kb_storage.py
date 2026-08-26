"""On-disk storage for uploaded knowledge-base documents."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config.settings import Settings


def _sanitize_filename(name: str) -> str:
    base = Path(name).name.strip() or "document"
    cleaned = re.sub(r"[^\w.\-()+ ]+", "_", base, flags=re.UNICODE)
    return cleaned[:200] or "document"


class KbStorageService:
    def __init__(self, settings: Settings) -> None:
        override = (settings.kb_storage_dir or settings.rashid_data_dir or "").strip()
        if override:
            root = Path(override)
        else:
            root = Path(__file__).resolve().parents[2] / "data"
        self.root = root / "kb"

    def doc_dir(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID) -> Path:
        return self.root / str(tenant_id) / str(kb_id) / str(doc_id)

    def save_bytes(
        self,
        *,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        doc_id: uuid.UUID,
        filename: str,
        data: bytes,
    ) -> Path:
        directory = self.doc_dir(tenant_id, kb_id, doc_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _sanitize_filename(filename)
        path.write_bytes(data)
        return path

    def delete_doc_dir(self, tenant_id: uuid.UUID, kb_id: uuid.UUID, doc_id: uuid.UUID) -> None:
        directory = self.doc_dir(tenant_id, kb_id, doc_id)
        if not directory.exists():
            return
        for child in directory.iterdir():
            if child.is_file():
                child.unlink(missing_ok=True)
        directory.rmdir()
