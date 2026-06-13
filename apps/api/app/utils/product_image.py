"""Normalize and resolve Uzum product preview image URLs."""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

_PRODUCT_IMAGE_HOST_SUFFIXES = (".uzum.uz", ".uzummarket.uz")
_UZUM_CDN_IMAGE_VARIANTS = (
    "t_product_240_high.jpg",
    "original.jpg",
    "t_product_540_high.jpg",
)
_BARE_HASH_RE = re.compile(r"^[a-zA-Z0-9_-]{8,}$")


def _str_val(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    return text


def is_bare_uzum_cdn_path(path: str) -> bool:
    """images.uzum.uz/{hash} without file extension needs a suffix."""
    cleaned = (path or "").strip("/")
    if not cleaned or "/" in cleaned:
        return False
    return "." not in cleaned.split("/")[-1]


def normalize_product_image_url(raw: Any) -> Optional[str]:
    """Normalize preview URL from left-out / Uzum API."""
    url = _str_val(raw)
    if not url or url.lower() in {"nan", "none", "null", "-"}:
        return None

    if _BARE_HASH_RE.fullmatch(url):
        return f"https://images.uzum.uz/{url}"

    if url.startswith("//"):
        url = f"https:{url}"
    elif url.startswith("/"):
        url = f"https://images.uzum.uz{url}"

    if url.lower().startswith("http://"):
        url = "https://" + url[7:]

    if url.lower().startswith("https://"):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("seller.") or host == "seller.uzum.uz":
            return None
        return url

    return None


def uzum_cdn_fetch_candidates(url: str) -> list[str]:
    normalized = normalize_product_image_url(url)
    if not normalized:
        return []
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if not host.endswith("images.uzum.uz"):
        return [normalized]
    if is_bare_uzum_cdn_path(parsed.path or ""):
        base = normalized.rstrip("/")
        return [f"{base}/{variant}" for variant in _UZUM_CDN_IMAGE_VARIANTS]
    return [normalized]


def resolve_product_image_url(raw: Any) -> Optional[str]:
    """Best display/storage URL (bare CDN hash → thumbnail path)."""
    normalized = normalize_product_image_url(raw)
    if not normalized:
        return None
    candidates = uzum_cdn_fetch_candidates(normalized)
    return candidates[0] if candidates else normalized


def is_allowed_product_image_host(hostname: Optional[str]) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    return any(host == suffix[1:] or host.endswith(suffix) for suffix in _PRODUCT_IMAGE_HOST_SUFFIXES)
