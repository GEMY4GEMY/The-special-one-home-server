"""Local PDF text extraction, preserving page references.

This module extracts embedded text only. Scanned pages require a separate
vision/OCR adapter and are not silently treated as empty curriculum.
"""
from io import BytesIO
from pypdf import PdfReader

MAX_PAGES = 300
MAX_PAGE_CHARS = 15000

def extract_pdf_pages(raw: bytes):
    if not raw.startswith(b"%PDF"):
        raise ValueError("Not a PDF file")
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise ValueError("PDF must contain between 1 and 300 pages")
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append({"page": index, "text": text[:MAX_PAGE_CHARS], "needs_vision": not bool(text)})
        return pages
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not read PDF") from exc
