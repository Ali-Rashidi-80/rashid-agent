"""Image OCR for knowledge-base ingest (local RapidOCR / Tesseract, optional Metis vision)."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import structlog

from app.config.settings import Settings
from app.services.metis import METIS_API_ROOT

logger = structlog.get_logger()


def ocr_image(path: Path, settings: Settings | None = None) -> str:
    """Return extracted text from an image path. Empty string if all engines fail."""
    text = _ocr_rapid(path)
    if text:
        return text
    text = _ocr_tesseract(path)
    if text:
        return text
    if settings and settings.api_key:
        text = _ocr_metis_vision(path, settings)
        if text:
            return text
    return ""


def _ocr_rapid(path: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        logger.info("kb_ocr_rapid_unavailable")
        return ""
    try:
        engine = RapidOCR()
        result, _ = engine(str(path))
    except Exception as exc:
        logger.warning("kb_ocr_rapid_failed", error=str(exc))
        return ""
    if not result:
        return ""
    lines: list[str] = []
    for item in result:
        # item: [box, text, score]
        if isinstance(item, list | tuple) and len(item) >= 2 and isinstance(item[1], str):
            piece = item[1].strip()
            if piece:
                lines.append(piece)
    return "\n".join(lines).strip()


def _ocr_tesseract(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        image = Image.open(path)
        # Prefer Persian+English when available; fall back to eng.
        for lang in ("fas+eng", "eng"):
            try:
                text = pytesseract.image_to_string(image, lang=lang) or ""
            except Exception:
                continue
            cleaned = text.strip()
            if cleaned:
                return cleaned
    except Exception as exc:
        logger.warning("kb_ocr_tesseract_failed", error=str(exc))
    return ""


def _ocr_metis_vision(path: Path, settings: Settings) -> str:
    """Use OpenAI-compatible vision chat on Metis for OCR (Persian-capable)."""
    try:
        raw = path.read_bytes()
        mime = "image/png"
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif suffix == ".webp":
            mime = "image/webp"
        b64 = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        url = f"{METIS_API_ROOT}/openai_chat_completion/chat/completions"
        model = (settings.kb_ocr_vision_model or "gpt-4o-mini").strip()
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL readable text from this image (OCR). "
                                "Reply with the text only, no commentary. "
                                "If no text is visible, reply with an empty string."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": 2048,
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            return content.strip()
    except Exception as exc:
        logger.warning("kb_ocr_metis_failed", error=str(exc))
    return ""


def render_probe_image(text: str, dest: Path) -> Path:
    """Helper for tests: draw clear Latin text onto a white PNG."""
    from PIL import Image, ImageDraw, ImageFont

    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 160), "white")
    draw = ImageDraw.Draw(img)
    try:
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((24, 56), text, fill="black", font=font)
    img.save(dest)
    return dest
