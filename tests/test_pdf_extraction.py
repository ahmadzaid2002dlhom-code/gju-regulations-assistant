from pathlib import Path

import fitz

from src.ingestion.pdf_extractor import _restore_arabic_reading_order, extract_pdf_pages


class FakeOCRProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str | None, bytes]] = []

    def extract_text(
        self,
        image_bytes: bytes,
        *,
        page_number: int,
        language: str | None,
    ) -> str:
        self.calls.append((page_number, language, image_bytes))
        return "المادة ١\nنص مستخرج من صورة"


def _write_pdf(path: Path, text: str | None) -> None:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_image_only_page_uses_ocr_fallback(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    _write_pdf(pdf_path, None)
    ocr = FakeOCRProvider()

    pages = extract_pdf_pages(pdf_path, ocr_provider=ocr, language="ar")

    assert pages[0].page_text == "المادة ١\nنص مستخرج من صورة"
    assert ocr.calls[0][0:2] == (1, "ar")
    assert ocr.calls[0][2].startswith(b"\x89PNG")


def test_searchable_page_does_not_call_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    _write_pdf(pdf_path, "Article 1 Searchable text")
    ocr = FakeOCRProvider()

    pages = extract_pdf_pages(pdf_path, ocr_provider=ocr, language="en")

    assert "Article 1" in pages[0].page_text
    assert ocr.calls == []


def test_arabic_visual_word_order_is_restored() -> None:
    extracted = "الأردنية الألمانية الجامعة في البكالوريوس الدرجة منح تعليمات"

    restored = _restore_arabic_reading_order(extracted)

    assert restored == "تعليمات منح الدرجة البكالوريوس في الجامعة الألمانية الأردنية"
