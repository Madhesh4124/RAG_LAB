import io

from PIL import Image

from app.services.image_loader import PDFImageLoader


class _FakeStorage:
    def __init__(self):
        self.saved = {}

    def save(self, data: bytes, extension: str) -> str:
        key = f"saved-image.{extension}"
        self.saved[key] = data
        return key


class _FakeImageObject:
    name = "figure.png"

    def __init__(self, data: bytes):
        self.data = data


class _FakePage:
    def __init__(self, images):
        self.images = images


class _FakeReader:
    def __init__(self, _):
        self.pages = [_FakePage([_FakeImageObject(_png_bytes())])]


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (128, 96), color="white").save(output, format="PNG")
    return output.getvalue()


def test_extract_pdf_images_returns_image_chunks(monkeypatch):
    storage = _FakeStorage()
    monkeypatch.setattr("app.services.image_loader.pypdf.PdfReader", _FakeReader)
    monkeypatch.setattr("app.services.image_loader.get_file_storage", lambda: storage)

    chunks = PDFImageLoader.extract_from_bytes(b"%PDF-fake", "sample.pdf")

    assert len(chunks) == 1
    assert chunks[0].text == "image://saved-image.png"
    assert chunks[0].metadata["modality"] == "image"
    assert chunks[0].metadata["page"] == 1
    assert chunks[0].metadata["image_width"] == 128
    assert chunks[0].metadata["image_height"] == 96
    assert "saved-image.png" in storage.saved
