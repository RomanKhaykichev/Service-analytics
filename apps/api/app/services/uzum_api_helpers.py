"""Shared Uzum API key validation helpers (no route imports)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

INVALID_UZUM_API_KEY = "invalid_uzum_api_key"
UZUM_SHOP_UNAVAILABLE = "uzum_shop_unavailable"
UZUM_KEY_INSUFFICIENT_ACCESS = "uzum_key_insufficient_access"
UZUM_HOST = "https://api-seller.uzum.uz"
API_BASE_URL = f"{UZUM_HOST}/api/seller-openapi"
REQUEST_TIMEOUT = 30
DEFAULT_AUTH_MODE = "authorization_raw"

UZUM_SYNC_REPORT_TYPES = ("sales", "expenses", "storage", "inventory_old")

_INVALID_KEY_MARKERS = (
    "invalid_uzum_api_key",
    "unauthorized",
    "uzum api 401",
)

_FORBIDDEN_MARKERS = (
    "forbidden-001",
    "shop is not available",
    "not available",
)


def normalize_api_key(raw: str) -> str:
    key = raw.strip()
    if key.lower().startswith("bearer "):
        return key[7:].strip()
    return key


def uzum_accept_language(preferred: Optional[str] = None) -> str:
    """Map app UI language to Uzum OpenAPI Accept-Language (ru | uz)."""
    raw = (preferred or "ru").strip().lower()
    if raw.startswith("uz"):
        return "uz"
    return "ru"


def uzum_error_means_invalid_key(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _INVALID_KEY_MARKERS)


def _headers_for_mode(
    api_key: str,
    mode: str = DEFAULT_AUTH_MODE,
    *,
    accept_language: Optional[str] = None,
) -> dict[str, str]:
    base = {
        "Accept": "application/json",
        "Accept-Language": uzum_accept_language(accept_language),
    }
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


def _request_id_from_headers(response: requests.Response) -> Optional[str]:
    for key in ("x-request-id", "X-Request-Id", "request-id", "Request-Id"):
        value = response.headers.get(key)
        if value:
            return value
    return None


def _log_uzum_response(
    *,
    method: str,
    path: str,
    shop_ids: Optional[list[int]],
    response: requests.Response,
) -> None:
    request_id = _request_id_from_headers(response)
    body = _response_body(response)
    body_preview = body if isinstance(body, str) else str(body)
    if len(body_preview) > 500:
        body_preview = body_preview[:500] + "…"
    logger.info(
        "Uzum API %s %s shopIds=%s status=%s request_id=%s",
        method,
        path,
        shop_ids,
        response.status_code,
        request_id,
    )
    if response.status_code >= 400:
        logger.warning(
            "Uzum API error %s %s shopIds=%s status=%s request_id=%s body=%s",
            method,
            path,
            shop_ids,
            response.status_code,
            request_id,
            body_preview,
        )


def build_query_params(
    base: dict[str, Any],
    shop_ids: Optional[list[int]] = None,
) -> list[tuple[str, Any]]:
    """Serialize query params; list values (shopIds, statuses, …) as repeated keys."""
    merged = dict(base)
    if shop_ids is not None:
        merged["shopIds"] = shop_ids
    pairs: list[tuple[str, Any]] = []
    for key, value in merged.items():
        if isinstance(value, list):
            for item in value:
                pairs.append((key, item))
        else:
            pairs.append((key, value))
    return pairs


def extract_shop_ids_from_shops_response(body: Any) -> list[int]:
    if isinstance(body, dict):
        for key in ("payload", "shops", "data", "items"):
            inner = body.get(key)
            if isinstance(inner, list):
                body = inner
                break
    if not isinstance(body, list):
        return []
    ids: list[int] = []
    for shop in body:
        if not isinstance(shop, dict):
            continue
        raw = shop.get("id")
        if raw is None:
            continue
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return ids


def _errors_indicate_forbidden(body: Any) -> bool:
    if isinstance(body, list):
        for entry in body:
            if not isinstance(entry, dict):
                continue
            code = str(entry.get("code") or "")
            message = str(entry.get("message") or "")
            if code == "forbidden-001" or "not available" in message.lower():
                return True
        return False
    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list):
            for entry in errors:
                if not isinstance(entry, dict):
                    continue
                code = str(entry.get("code") or "")
                message = str(entry.get("message") or "")
                if code == "forbidden-001" or "not available" in message.lower():
                    return True
    text = str(body).lower()
    return any(marker in text for marker in _FORBIDDEN_MARKERS)


def _body_forbidden_detail(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    if _errors_indicate_forbidden(body.get("errors")):
        return str(body.get("errors") or body)
    payload = body.get("payload")
    if isinstance(payload, dict) and _errors_indicate_forbidden(payload.get("errors")):
        return str(payload.get("errors") or payload)
    return None


def _is_transient_uzum_error(message: str) -> bool:
    lower = message.lower()
    return any(
        token in lower
        for token in (
            "ssl",
            "connection",
            "timeout",
            "timed out",
            "connectionpool",
            "max retries",
            "temporarily unavailable",
            "502",
            "503",
            "504",
        )
    )


def _finance_probe_date_range() -> tuple[int, int]:
    from app.services.uzum_time import calendar_date_to_epoch_ms, uz_now

    today = uz_now().date()
    date_from_ms = calendar_date_to_epoch_ms(f"{today.year}-01-01", end_of_day=False)
    date_to_ms = calendar_date_to_epoch_ms(today.isoformat(), end_of_day=True)
    assert date_from_ms is not None and date_to_ms is not None
    return date_from_ms, date_to_ms


def _response_means_forbidden(status: int, body: Any) -> bool:
    if _errors_indicate_forbidden(body):
        return True
    if isinstance(body, dict):
        payload = body.get("payload")
        if isinstance(payload, dict) and _errors_indicate_forbidden(payload.get("errors")):
            return True
    if status == 403:
        return _errors_indicate_forbidden(body)
    return status >= 400 and _errors_indicate_forbidden(body)


def _error_is_definite_forbidden(err: str) -> bool:
    lower = err.lower()
    return any(
        marker in lower
        for marker in (
            "forbidden-001",
            "shop is not available",
            "недоступен",
            "not available",
        )
    )


_FINANCE_ORDER_STATUSES = [
    "TO_WITHDRAW",
    "PROCESSING",
    "CANCELED",
    "PARTIALLY_CANCELLED",
]


def _probe_finance_endpoint(
    api_key: str,
    path: str,
    shop_id: int,
    *,
    orders: bool = False,
) -> tuple[bool, Optional[str]]:
    """Probe finance API with shopIds and date format fallbacks (ms → sec → none)."""
    date_from_ms, date_to_ms = _finance_probe_date_range()
    base: dict[str, Any] = {"page": 0, "size": 1, "shopIds": [shop_id]}
    if orders:
        base["group"] = False
        base["statuses"] = _FINANCE_ORDER_STATUSES

    date_variants: list[dict[str, Any]] = [
        {"dateFrom": date_from_ms, "dateTo": date_to_ms},
        {"dateFrom": date_from_ms // 1000, "dateTo": date_to_ms // 1000},
        {},
    ]
    last_err: Optional[str] = None
    for dates in date_variants:
        ok, err = _probe_get(api_key, path, {**base, **dates})
        if ok:
            return True, None
        last_err = err
        if err == INVALID_UZUM_API_KEY:
            return False, err
        if err and _error_is_definite_forbidden(err):
            return False, err
    return False, last_err


def _probe_get(
    api_key: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
) -> tuple[bool, Optional[str]]:
    url = _resolve_url(path)
    headers = _headers_for_mode(api_key, DEFAULT_AUTH_MODE)
    shop_ids: Optional[list[int]] = None
    if params and "shopIds" in params:
        raw = params["shopIds"]
        shop_ids = raw if isinstance(raw, list) else [raw]
    query = build_query_params(params or {}) if params else None
    try:
        response = requests.get(url, headers=headers, params=query, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return False, str(exc)

    _log_uzum_response(method="GET", path=path, shop_ids=shop_ids, response=response)
    body = _response_body(response)
    if response.status_code == 200:
        forbidden = _body_forbidden_detail(body)
        if forbidden:
            return False, forbidden
        return True, None
    if _response_means_forbidden(response.status_code, body):
        return False, str(body) if body else f"HTTP {response.status_code}"
    if response.status_code == 401:
        return False, INVALID_UZUM_API_KEY
    return False, str(body) if body else f"HTTP {response.status_code}"


@dataclass
class ShopAccessProbe:
    shop_id: int
    shops_ok: bool = False
    product_ok: bool = False
    orders_ok: bool = False
    expenses_ok: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class ApiKeyAccessResult:
    ok: bool
    shop_ids: list[int]
    error: Optional[str] = None
    probes: list[ShopAccessProbe] = field(default_factory=list)


def _probe_single_shop(api_key: str, shop_id: int) -> ShopAccessProbe:
    probe = ShopAccessProbe(shop_id=shop_id, shops_ok=True)

    product_ok, product_err = _probe_get(
        api_key,
        f"/v1/product/shop/{shop_id}",
        {"page": 0, "size": 1, "filter": "ALL"},
    )
    probe.product_ok = product_ok
    if product_err:
        probe.errors.append(f"product: {product_err}")

    orders_ok, orders_err = _probe_finance_endpoint(
        api_key,
        "/v1/finance/orders",
        shop_id,
        orders=True,
    )
    probe.orders_ok = orders_ok
    if orders_err:
        probe.errors.append(f"orders: {orders_err}")

    expenses_ok, expenses_err = _probe_finance_endpoint(
        api_key,
        "/v1/finance/expenses",
        shop_id,
    )
    probe.expenses_ok = expenses_ok
    if expenses_err:
        probe.errors.append(f"expenses: {expenses_err}")
    return probe


def validate_api_key_access(api_key: str) -> ApiKeyAccessResult:
    """
    Full access probe for connect/sync:
    /v1/shops → shop list, then product + finance for each shop until one passes.
    """
    url = _resolve_url("/v1/shops")
    headers = _headers_for_mode(api_key, DEFAULT_AUTH_MODE)
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return ApiKeyAccessResult(ok=False, shop_ids=[], error=str(exc))

    _log_uzum_response(method="GET", path="/v1/shops", shop_ids=None, response=response)
    body = _response_body(response)
    if response.status_code != 200:
        detail = body if isinstance(body, str) else str(body)
        if len(detail) > 400:
            detail = detail[:400] + "…"
        if response.status_code == 401:
            return ApiKeyAccessResult(ok=False, shop_ids=[], error=INVALID_UZUM_API_KEY)
        return ApiKeyAccessResult(ok=False, shop_ids=[], error=detail or f"HTTP {response.status_code}")

    shop_ids = extract_shop_ids_from_shops_response(body)
    logger.info("Uzum API /v1/shops returned shop_ids=%s", shop_ids)
    if not shop_ids:
        return ApiKeyAccessResult(
            ok=False,
            shop_ids=[],
            error="Не найдены магазины в Uzum API (/v1/shops).",
        )

    probes: list[ShopAccessProbe] = []
    for shop_id in shop_ids:
        probe = _probe_single_shop(api_key, shop_id)
        probes.append(probe)
        if probe.orders_ok:
            logger.info(
                "Uzum API key access OK for shop_id=%s (product=%s expenses=%s)",
                shop_id,
                probe.product_ok,
                probe.expenses_ok,
            )
            return ApiKeyAccessResult(ok=True, shop_ids=shop_ids, probes=probes)

    flat_errors = [e for p in probes for e in p.errors]
    if flat_errors and all(_is_transient_uzum_error(e) for e in flat_errors):
        return ApiKeyAccessResult(
            ok=False,
            shop_ids=shop_ids,
            error=flat_errors[0],
            probes=probes,
        )

    logger.warning(
        "Uzum API key insufficient access shop_ids=%s probes=%s",
        shop_ids,
        [
            {
                "shop_id": p.shop_id,
                "product": p.product_ok,
                "orders": p.orders_ok,
                "expenses": p.expenses_ok,
                "errors": p.errors,
            }
            for p in probes
        ],
    )
    return ApiKeyAccessResult(
        ok=False,
        shop_ids=shop_ids,
        error=UZUM_KEY_INSUFFICIENT_ACCESS,
        probes=probes,
    )


def validate_api_key_shops(api_key: str) -> tuple[bool, Optional[str], Optional[int]]:
    """Fast check: GET /v1/shops only (before background sync; scope probed in worker)."""
    url = _resolve_url("/v1/shops")
    headers = _headers_for_mode(api_key, DEFAULT_AUTH_MODE)
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return False, str(exc), None

    _log_uzum_response(method="GET", path="/v1/shops", shop_ids=None, response=response)
    body = _response_body(response)
    if response.status_code == 200:
        shop_ids = extract_shop_ids_from_shops_response(body)
        if not shop_ids:
            return False, "Не найдены магазины в Uzum API (/v1/shops).", 200
        return True, None, 200

    detail = body if isinstance(body, str) else str(body)
    if len(detail) > 400:
        detail = detail[:400] + "…"
    if response.status_code == 401:
        return False, INVALID_UZUM_API_KEY, 401
    return False, detail or f"HTTP {response.status_code}", response.status_code


def validate_api_key(api_key: str) -> tuple[bool, Optional[str], Optional[int]]:
    """Full access probe (OpenAPI explore, strict connect checks)."""
    access = validate_api_key_access(api_key)
    if access.ok:
        return True, None, 200
    if access.error == INVALID_UZUM_API_KEY:
        return False, INVALID_UZUM_API_KEY, 401
    return False, access.error, None
