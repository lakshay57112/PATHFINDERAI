"""Secure file uploads: type sniffing by magic bytes, size limits, random names, encryption at rest."""
from __future__ import annotations

import io
import logging
import secrets

from app.core.config import get_settings
from app.core.errors import InvalidFile
from app.core.security import decrypt_bytes, encrypt_bytes

log = logging.getLogger("pathfinder.storage")

SIGNATURES = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]


def sniff(data: bytes) -> str | None:
    for sig, mime in SIGNATURES:
        if data.startswith(sig):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate(data: bytes, filename: str | None) -> str:
    s = get_settings()
    if not data:
        raise InvalidFile("The uploaded file is empty.")
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise InvalidFile(f"Files must be smaller than {s.max_upload_mb} MB.", status_code=413)
    mime = sniff(data)
    if not mime:
        raise InvalidFile("Please upload a PDF, PNG, JPEG or WebP file.")
    return mime


def save_encrypted(data: bytes) -> str:
    s = get_settings()
    s.upload_dir.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(16)
    (s.upload_dir / f"{key}.bin").write_bytes(encrypt_bytes(data))
    return key


def load_decrypted(key: str) -> bytes:
    path = get_settings().upload_dir / f"{key}.bin"
    return decrypt_bytes(path.read_bytes())


def delete(key: str | None) -> None:
    if not key:
        return
    path = get_settings().upload_dir / f"{key}.bin"
    path.unlink(missing_ok=True)


def extract_text(data: bytes, mime: str) -> str:
    """Best-effort text extraction. PDFs via pypdf; images via Tesseract only if installed."""
    try:
        if mime == "application/pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages[:5])[:20000]
        # Images: OCR only when Tesseract is installed; otherwise we rely on the name/issuer the user entered.
        try:
            import pytesseract
            from PIL import Image

            return pytesseract.image_to_string(Image.open(io.BytesIO(data)))[:20000]
        except Exception:
            return ""
    except Exception as exc:  # malformed files shouldn't crash the request
        log.info("text extraction failed: %s", exc)
        raise InvalidFile("We couldn't read that file. Is it a valid, unencrypted PDF or image?") from exc
