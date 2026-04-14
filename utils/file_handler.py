"""
utils/file_handler.py
---------------------
Handles text extraction from uploaded .txt and .pdf files.

Uses:
  - Built-in Python for .txt files
  - PyMuPDF (fitz) for .pdf files — fast, no Java dependency
"""

import logging
import os
import chardet
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"txt", "pdf"}


def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def extract_text_from_file(filepath: str) -> str:
    """
    Extract plain text from a .txt or .pdf file.

    Args:
        filepath : Absolute path to the uploaded file.

    Returns:
        Extracted text as a string.

    Raises:
        ValueError: If the file type is unsupported or text extraction fails.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        return _extract_from_txt(filepath)
    elif ext == ".pdf":
        return _extract_from_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Only .txt and .pdf are allowed.")


def _extract_from_txt(filepath: str) -> str:
    """Read a .txt file with automatic encoding detection."""
    try:
        # Detect encoding first
        with open(filepath, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"
        logger.info("Detected encoding '%s' for %s", encoding, filepath)

        text = raw.decode(encoding, errors="replace")
        text = text.strip()

        if not text:
            raise ValueError("The uploaded .txt file appears to be empty.")

        return text

    except Exception as exc:
        logger.error("Failed to read .txt file '%s': %s", filepath, exc)
        raise ValueError(f"Could not read text file: {exc}") from exc


def _extract_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        doc = fitz.open(filepath)
        pages_text = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            if page_text.strip():
                pages_text.append(page_text.strip())

        doc.close()

        if not pages_text:
            raise ValueError(
                "No readable text found in the PDF. "
                "The file may be image-based (scanned) or password-protected."
            )

        full_text = "\n\n".join(pages_text)
        logger.info(
            "Extracted %d characters from %d pages of '%s'",
            len(full_text), len(pages_text), filepath
        )
        return full_text

    except fitz.FileDataError as exc:
        logger.error("Invalid PDF file '%s': %s", filepath, exc)
        raise ValueError(f"Invalid or corrupted PDF file: {exc}") from exc
    except Exception as exc:
        logger.error("Failed to extract PDF text from '%s': %s", filepath, exc)
        raise ValueError(f"Could not read PDF file: {exc}") from exc


def cleanup_file(filepath: str) -> None:
    """Delete a temporary uploaded file after processing."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info("Cleaned up temp file: %s", filepath)
    except Exception as exc:
        logger.warning("Could not delete temp file '%s': %s", filepath, exc)
