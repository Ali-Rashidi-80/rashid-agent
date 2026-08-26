"""Honest OCR tests — RapidOCR must extract rendered Latin text."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.kb_ocr import ocr_image, render_probe_image
from app.services.kb_text import PartialTextExtraction, extract_text


def test_rapidocr_reads_rendered_latin_text(tmp_path: Path):
    probe = render_probe_image("LEAVE_POLICY_20_DAYS", tmp_path / "ocr.png")
    text = ocr_image(probe, settings=None)
    normalized = "".join(text.split())
    assert "LEAVE_POLICY_20_DAYS" in normalized


def test_blankish_tiny_png_raises_partial(tmp_path: Path):
    # 1x1 PNG has no glyphs → OCR empty → PartialTextExtraction
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path = tmp_path / "blank.png"
    path.write_bytes(png)
    with pytest.raises(PartialTextExtraction) as exc:
        extract_text(path, mime="image/png")
    assert "image_ocr_empty" in str(exc.value)
