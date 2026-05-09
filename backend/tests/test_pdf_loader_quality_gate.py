from app.services.pdf_loader import PDFPage, _pypdf_text_quality_ok


def _mk_page(text: str) -> PDFPage:
    return PDFPage(page_num=0, text=text, metadata={})


def test_quality_gate_fails_when_total_chars_below_default_for_regular_docs(monkeypatch):
    monkeypatch.delenv("PDF_AUTO_MIN_TEXT_PAGE_RATIO", raising=False)
    monkeypatch.delenv("PDF_AUTO_MIN_TOTAL_CHARS", raising=False)
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_MAX_PAGES", raising=False)
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_CHARS_PER_PAGE", raising=False)

    pages = [_mk_page("a" * 120), _mk_page("b" * 120), _mk_page("c" * 120)]

    assert _pypdf_text_quality_ok(pages, total_pages=3) is False


def test_quality_gate_passes_short_doc_with_scaled_threshold(monkeypatch):
    monkeypatch.delenv("PDF_AUTO_MIN_TEXT_PAGE_RATIO", raising=False)
    monkeypatch.delenv("PDF_AUTO_MIN_TOTAL_CHARS", raising=False)
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_MAX_PAGES", raising=False)
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_CHARS_PER_PAGE", raising=False)

    pages = [_mk_page("a" * 170)]

    # Default short-doc threshold is 150 chars for a single page.
    assert _pypdf_text_quality_ok(pages, total_pages=1) is True


def test_quality_gate_keeps_ratio_requirement(monkeypatch):
    monkeypatch.setenv("PDF_AUTO_MIN_TEXT_PAGE_RATIO", "0.8")
    monkeypatch.setenv("PDF_AUTO_MIN_TOTAL_CHARS", "200")
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_MAX_PAGES", raising=False)
    monkeypatch.delenv("PDF_AUTO_SHORT_DOC_CHARS_PER_PAGE", raising=False)

    pages = [_mk_page("a" * 220)]  # One non-empty page out of three total pages.

    assert _pypdf_text_quality_ok(pages, total_pages=3) is False
