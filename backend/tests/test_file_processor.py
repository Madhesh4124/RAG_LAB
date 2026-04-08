from app.utils.file_processor import FileProcessor


def test_extract_pdf_pages_uses_legacy_text_fallback_for_flat_rows():
    pages = FileProcessor.extract_pdf_pages(
        "Legacy extracted text with an em dash — and no PDF header.",
        filename="legacy.pdf",
    )

    assert len(pages) == 1
    assert pages[0]["text"].startswith("Legacy extracted text")
    assert pages[0]["metadata"]["source_type"] == "legacy_text"
