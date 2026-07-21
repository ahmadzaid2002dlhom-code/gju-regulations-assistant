from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import httpx


def calculate_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_pdf_filename(title: str, url: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    if not slug:
        slug = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{slug[:100]}.pdf"


def download_pdf(url: str, destination: Path) -> bytes:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    content = response.content
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not content.startswith(b"%PDF"):
        raise ValueError(f"The resource at {url} is not a PDF.")

    destination.write_bytes(content)
    return content
