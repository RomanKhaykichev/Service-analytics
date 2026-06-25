"""Proxy and explorer for Uzum Seller OpenAPI (api-seller.uzum.uz)."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Literal, Optional
from uuid import UUID

from datetime import date

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.models.user import User
from app.services.uzum_export import (
    ShopUnavailableError,
    UzumRateLimitError,
    build_report,
    build_xlsx_bytes,
    report_metadata,
)
from app.services.uzum_api_helpers import (
    INVALID_UZUM_API_KEY,
    UZUM_KEY_INSUFFICIENT_ACCESS,
    UZUM_SHOP_UNAVAILABLE,
    normalize_api_key,
    uzum_error_means_invalid_key,
    validate_api_key,
    validate_api_key_shops,
)
from app.services.uzum_sync import (
    enqueue_manual_uzum_sync_job,
    get_uzum_sync_log_status,
    run_uzum_sync_for_user,
    user_has_running_manual_sync,
    _insert_running_sync_log,
)
from app.services.uzum_time import timezone_metadata

logger = logging.getLogger(__name__)
router = APIRouter()

UZUM_HOST = "https://api-seller.uzum.uz"
OPENAPI_SPEC_URL = f"{UZUM_HOST}/api/seller-openapi/swagger/api-docs"
API_BASE_URL = f"{UZUM_HOST}/api/seller-openapi"
REQUEST_TIMEOUT = 30
def _invalid_key_http_exception() -> HTTPException:
    return HTTPException(status_code=400, detail=INVALID_UZUM_API_KEY)


def _shop_unavailable_http_exception() -> HTTPException:
    return HTTPException(status_code=403, detail=UZUM_SHOP_UNAVAILABLE)


def _key_insufficient_access_http_exception() -> HTTPException:
    return HTTPException(status_code=403, detail=UZUM_KEY_INSUFFICIENT_ACCESS)

# From Uzum OpenAPI: Authorization header, token WITHOUT "Bearer " prefix.
DEFAULT_AUTH_MODE = "authorization_raw"
AuthMode = Literal["bearer", "authorization_raw", "x-api-key", "x-api-key-alt", "api-key"]


def _warnings_response_header(warnings: list[str]) -> str:
    """HTTP headers must be latin-1; encode UTF-8 warnings as base64 JSON."""
    payload = json.dumps(warnings, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def _get_user_uzum_api_key(db: Session, user_id: UUID) -> Optional[str]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    key = user.uzum_seller_api_key
    return key.strip() if isinstance(key, str) and key.strip() else None


def _save_user_uzum_api_key(db: Session, user_id: UUID, api_key: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.uzum_seller_api_key = api_key
    db.commit()


def _headers_for_mode(api_key: str, mode: AuthMode) -> dict[str, str]:
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


def _parse_endpoints(spec: dict[str, Any]) -> list[dict[str, Any]]:
    paths = spec.get("paths") or {}
    endpoints: list[dict[str, Any]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(details, dict):
                details = {}
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary") or details.get("operationId") or "",
                    "tags": details.get("tags") or [],
                }
            )
    endpoints.sort(key=lambda e: ((e.get("tags") or [""])[0], e["path"], e["method"]))
    return endpoints


def _response_body(response: requests.Response) -> Any:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def _load_openapi_spec() -> dict[str, Any]:
    try:
        response = requests.get(
            OPENAPI_SPEC_URL,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось загрузить спецификацию Uzum: {exc}",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Спецификация Uzum недоступна (HTTP {response.status_code})",
        )

    body = _response_body(response)
    if not isinstance(body, dict) or not body.get("paths"):
        raise HTTPException(status_code=502, detail="Некорректный ответ спецификации Uzum OpenAPI")
    return body


class OpenApiExploreBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)


class UzumApiKeyBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)


class UzumApiKeyResponse(BaseModel):
    api_key: Optional[str] = None
    has_key: bool = False


@router.get("/uzum-seller/api-key", response_model=UzumApiKeyResponse)
def get_uzum_api_key(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Return saved Uzum Seller API key for the current user."""
    key = _get_user_uzum_api_key(db, user_id)
    return UzumApiKeyResponse(api_key=key, has_key=bool(key))


@router.put("/uzum-seller/api-key", response_model=UzumApiKeyResponse)
def save_uzum_api_key(
    body: UzumApiKeyBody,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Save Uzum Seller API key for the current user (overwrites previous key)."""
    api_key = normalize_api_key(body.api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    _save_user_uzum_api_key(db, user_id, api_key)
    return UzumApiKeyResponse(api_key=api_key, has_key=True)


class UzumProxyBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)
    auth_mode: AuthMode = DEFAULT_AUTH_MODE
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    path: str = Field(min_length=1, max_length=2048)
    query: Optional[dict[str, str]] = None


@router.post("/uzum-seller/openapi")
def explore_uzum_openapi(
    body: OpenApiExploreBody,
    user_id: UUID = Depends(require_user),
):
    """Load Uzum Seller OpenAPI spec and validate API token."""
    _ = user_id
    api_key = normalize_api_key(body.api_key)
    spec = _load_openapi_spec()
    key_valid, key_error, key_status = validate_api_key(api_key)
    info = spec.get("info") or {}

    return {
        "auth_mode": DEFAULT_AUTH_MODE,
        "key_valid": key_valid,
        "key_error": key_error,
        "key_status": key_status,
        "openapi_version": spec.get("openapi") or spec.get("swagger"),
        "info_title": info.get("title"),
        "info_description": info.get("description"),
        "servers": spec.get("servers") or [],
        "endpoints": _parse_endpoints(spec),
        "tags": spec.get("tags") or [],
        "auth_hint": "Передайте токен в заголовке Authorization без префикса Bearer",
    }


@router.post("/uzum-seller/proxy")
def proxy_uzum_request(
    body: UzumProxyBody,
    user_id: UUID = Depends(require_user),
):
    """Proxy a single request to Uzum Seller API (for exploration)."""
    _ = user_id
    api_key = normalize_api_key(body.api_key)
    headers = _headers_for_mode(api_key, body.auth_mode)
    method = body.method.upper()
    url = _resolve_url(body.path.strip())

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=body.query or None,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка соединения с Uzum API: {exc}") from exc

    return {
        "url": response.url,
        "status_code": response.status_code,
        "ok": response.ok,
        "data": _response_body(response),
    }


class UzumExportBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)
    report_type: Literal["sales", "expenses", "storage", "inventory_old"]
    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    shop_ids: Optional[list[int]] = None
    preview_limit: Optional[int] = Field(default=None, ge=1, le=500)


@router.get("/uzum-seller/reports/templates")
def list_uzum_report_templates(user_id: UUID = Depends(require_user)):
    """Column templates matching uploaded XLSX report types."""
    _ = user_id
    return {"reports": report_metadata(), **timezone_metadata()}


@router.post("/uzum-seller/reports/export")
def export_uzum_report(
    body: UzumExportBody,
    user_id: UUID = Depends(require_user),
):
    """Download XLSX in the same shape as manual Uzum reports (bold = no API field)."""
    _ = user_id
    api_key = normalize_api_key(body.api_key)
    try:
        columns, rows, filename, warnings = build_report(
            body.report_type,
            api_key,
            date_from=body.date_from,
            date_to=body.date_to,
            shop_ids=body.shop_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ShopUnavailableError as exc:
        raise _invalid_key_http_exception() from exc
    except UzumRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
        if uzum_error_means_invalid_key(exc):
            raise _invalid_key_http_exception() from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    xlsx = build_xlsx_bytes(body.report_type, columns, rows)
    if warnings:
        logger.info("Uzum export warnings: %s", warnings)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if warnings:
        headers["X-Uzum-Warnings"] = _warnings_response_header(warnings)
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/uzum-seller/reports/preview")
def preview_uzum_report(
    body: UzumExportBody,
    user_id: UUID = Depends(require_user),
):
    """Preview first rows; column names include mapped flag for UI styling."""
    _ = user_id
    api_key = normalize_api_key(body.api_key)
    limit = body.preview_limit or 50
    try:
        columns, rows, filename, warnings = build_report(
            body.report_type,
            api_key,
            date_from=body.date_from,
            date_to=body.date_to,
            shop_ids=body.shop_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ShopUnavailableError as exc:
        raise _invalid_key_http_exception() from exc
    except UzumRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
        if uzum_error_means_invalid_key(exc):
            raise _invalid_key_http_exception() from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "file_name": filename,
        "row_count": len(rows),
        "columns": [{"name": c.name, "mapped": c.mapped} for c in columns],
        "rows": rows[:limit],
        "warnings": warnings,
        **timezone_metadata(),
    }


class UzumSyncBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)
    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD, default: Jan 1 current year")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD, default: today")


class UzumSyncStartResponse(BaseModel):
    ok: bool = True
    sync_id: str
    status: str = "running"


class UzumSyncStatusResponse(BaseModel):
    sync_id: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    upload_batch_id: Optional[str] = None
    imported: Optional[dict[str, int]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


def _resolve_sync_dates(body: UzumSyncBody) -> tuple[str, str]:
    today = date.today()
    date_from = body.date_from or f"{today.year}-01-01"
    date_to = body.date_to or today.isoformat()
    return date_from, date_to


@router.post("/uzum-seller/reports/sync/start", response_model=UzumSyncStartResponse)
def start_uzum_reports_sync(
    body: UzumSyncBody,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Start Uzum sync in background; poll GET .../sync/status/{sync_id} for result."""
    api_key = normalize_api_key(body.api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    date_from, date_to = _resolve_sync_dates(body)

    key_valid, key_error, key_status = validate_api_key_shops(api_key)
    if not key_valid:
        raise HTTPException(
            status_code=400 if key_error == INVALID_UZUM_API_KEY else 502,
            detail=key_error or INVALID_UZUM_API_KEY,
        )

    _save_user_uzum_api_key(db, user_id, api_key)

    if user_has_running_manual_sync(db, user_id):
        raise HTTPException(
            status_code=409,
            detail="Синхронизация уже выполняется. Подождите завершения текущей загрузки.",
        )

    log_id, _ = _insert_running_sync_log(db, user_id=user_id, trigger="manual")

    background_tasks.add_task(
        enqueue_manual_uzum_sync_job,
        log_id,
        user_id,
        api_key=api_key,
        date_from=date_from,
        date_to=date_to,
    )

    return UzumSyncStartResponse(sync_id=log_id, status="running")


@router.get("/uzum-seller/sync/active")
def get_active_uzum_sync(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Whether a Uzum sync is running for the current user (for dashboard UI)."""
    running = user_has_running_manual_sync(db, user_id)
    return {"running": running}


@router.get("/uzum-seller/reports/sync/status/{sync_id}", response_model=UzumSyncStatusResponse)
def get_uzum_reports_sync_status(
    sync_id: str,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Poll status of a manual Uzum sync started via POST .../sync/start."""
    row = get_uzum_sync_log_status(db, user_id, sync_id)
    if not row:
        raise HTTPException(status_code=404, detail="Sync job not found")

    response = UzumSyncStatusResponse(
        sync_id=row["sync_id"],
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        error_message=row["error_message"],
        upload_batch_id=row["upload_batch_id"],
    )
    return response


@router.post("/uzum-seller/reports/sync")
def sync_uzum_reports_to_service(
    body: UzumSyncBody,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Fetch four Uzum reports (YTD by default) and import them into the service."""
    api_key = normalize_api_key(body.api_key)
    today = date.today()
    date_from = body.date_from or f"{today.year}-01-01"
    date_to = body.date_to or today.isoformat()

    key_valid, key_error, _ = validate_api_key_shops(api_key)
    if not key_valid:
        raise HTTPException(
            status_code=400 if key_error == INVALID_UZUM_API_KEY else 502,
            detail=key_error or INVALID_UZUM_API_KEY,
        )

    _save_user_uzum_api_key(db, user_id, api_key)

    if user_has_running_manual_sync(db, user_id):
        raise HTTPException(
            status_code=409,
            detail="Синхронизация уже выполняется. Подождите завершения текущей загрузки.",
        )

    try:
        sync_result = run_uzum_sync_for_user(
            db,
            user_id,
            api_key=api_key,
            date_from=date_from,
            date_to=date_to,
            trigger="manual",
            skip_key_validation=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ShopUnavailableError as exc:
        raise _shop_unavailable_http_exception() from exc
    except UzumRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
        if uzum_error_means_invalid_key(exc):
            raise _invalid_key_http_exception() from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = sync_result.get("status")
    if status == "skipped":
        raise HTTPException(status_code=403, detail=sync_result.get("error") or "Sync skipped")
    if status == "failed":
        err = sync_result.get("error") or "Sync failed"
        if err == INVALID_UZUM_API_KEY:
            raise _invalid_key_http_exception()
        if err == UZUM_SHOP_UNAVAILABLE:
            raise _shop_unavailable_http_exception()
        if err == UZUM_KEY_INSUFFICIENT_ACCESS:
            raise _key_insufficient_access_http_exception()
        if "429" in str(err).lower() or "rate" in str(err).lower():
            raise HTTPException(status_code=429, detail=err)
        raise HTTPException(status_code=500, detail=err)

    return {
        "ok": True,
        "upload_batch_id": sync_result.get("upload_batch_id"),
        "imported": sync_result.get("imported"),
        "date_from": sync_result.get("date_from", date_from),
        "date_to": sync_result.get("date_to", date_to),
        **timezone_metadata(),
    }
