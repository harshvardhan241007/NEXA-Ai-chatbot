"""
Reads plain text out of .txt and .pdf files so they can be indexed by
the RAG module.
"""

import os
from .logger import get_logger

log = get_logger(__name__)


class UnsupportedFileType(ValueError):
    pass


def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def load_document(path: str) -> str:
    """Dispatch to the right reader based on file extension."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        text = read_txt(path)
    elif ext == ".pdf":
        text = read_pdf(path)
    else:
        raise UnsupportedFileType(f"Unsupported file type: {ext}")

    log.info("Loaded document %s (%d characters)", path, len(text))
    return text
