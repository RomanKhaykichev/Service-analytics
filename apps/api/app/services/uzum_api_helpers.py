"""Shared Uzum API key validation helpers (no route imports)."""

from __future__ import annotations

from typing import Any, Optional

import requests

INVALID_UZUM_API_KEY = "invalid_uzum_api_key"
UZUM_SHOP_UNAVAILABLE = "uzum_shop_unavailable"
UZUM_HOST = "https://api-seller.uzum.uz"
API_BASE_URL = f"{UZUM_HOST}/api/seller-openapi"
REQUEST_TIMEOUT = 30
DEFAULT_AUTH_MODE = "authorization_raw"

UZUM_SYNC_REPORT_TYPES = ("inventory_old", "sales", "expenses", "storage")

_INVALID_KEY_MARKERS = (
    "invalid_uzum_api_key",
    "unauthorized",
    "uzum api 401",
)


def normalize_api_key(raw: str) -> str:
    key = raw.strip()
    if key.lower().startswith("bearer "):
        return key[7:].strip()
    return key


def uzum_error_means_invalid_key(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _INVALID_KEY_MARKERS)


def _headers_for_mode(api_key: str, mode: str = DEFAULT_AUTH_MODE) -> dict[str, str]:
    base = {"Accept": "application/json", "Accept-Language": "ru-RU"}
    if mode == "bearer":
        return {**base, "Authorization": f"Bearer {api_key}"}
    if mode == "authorization_raw":
        return {**base, "Authorization": api_key}
    if mode == "x-api-key":
        return {**base, "X-API-Key": api_key}
    if mode == "x-api-key-alt":
        return {**base, "X-Api-Key": api_key}
    return {**base, "Api-Key": api_key}


def _resolve_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{API_BASE_URL.rstrip('/')}{normalized}"


def _response_body(response: requests.Response) -> Any:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def validate_api_key(api_key: str) -> tuple[bool, Optional[str], Optional[int]]:
    """Probe GET /v1/shops with the same Authorization format used for sync."""
    url = _resolve_url("/v1/shops")
    headers = _headers_for_mode(api_key, DEFAULT_AUTH_MODE)
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return False, str(exc), None

    if response.status_code == 200:
        return True, None, 200

    body = _response_body(response)
    detail = body if isinstance(body, str) else str(body)
    if len(detail) > 400:
        detail = detail[:400] + "…"
    return False, detail or f"HTTP {response.status_code}", response.status_code
