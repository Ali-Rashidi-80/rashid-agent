"""Extract plain text and chunk documents for KB ingest."""

from __future__ import annotations

from pathlib import Path

from app.config.settings import Settings, get_settings


class PartialTextExtraction(Exception):
    """Image/OCR-incomplete content — document may be stored as status=partial."""

    def __init__(self, message: str, placeholder: str = "") -> None:
        super().__init__(message)
        self.placeholder = placeholder


def extract_text(path: Path, mime: str = "", settings: Settings | None = None) -> str:
    suffix = path.suffix.lower()
    raw = path.read_bytes()
    if suffix in {".txt", ".md", ".markdown", ".csv"} or mime.startswith("text/"):
        return raw.decode("utf-8", errors="replace")
    if suffix == ".pdf" or mime == "application/pdf":
        return _extract_pdf(raw)
    if suffix in {".docx"} or mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }:
        return _extract_docx(raw)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"} or mime.startswith("image/"):
        return _extract_image(path, settings=settings or get_settings())
    # Best-effort fallback for unknown binary: try utf-8
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"unsupported document type: {suffix or mime}") from exc


def _extract_image(path: Path, settings: Settings) -> str:
    from app.services.kb_ocr import ocr_image

    text = ocr_image(path, settings=settings)
    if text.strip():
        return text.strip()
    raise PartialTextExtraction(
        "image_ocr_empty",
        placeholder=f"[Image OCR produced no text: {path.name}]",
    )


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF support requires pypdf") from exc
    import io

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("PDF contained no extractable text")
    return text


def _extract_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:
        raise ValueError("DOCX support requires python-docx") from exc
    import io

    document = docx.Document(io.BytesIO(data))
    text = "\n".join(p.text for p in document.paragraphs if p.text).strip()
    if not text:
        raise ValueError("DOCX contained no extractable text")
    return text


def chunk_text(text: str, *, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))
    cleaned = cleaned.strip()
    if not cleaned:
        return []
    if chunk_size < 64:
        chunk_size = 64
    if overlap < 0 or overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + chunk_size)
        if end < length:
            # Prefer breaking on whitespace near the end.
            window = cleaned[start:end]
            break_at = max(window.rfind("\n"), window.rfind(" "))
            if break_at > chunk_size // 2:
                end = start + break_at
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks
