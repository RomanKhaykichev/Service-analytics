"""Proxy and explorer for Uzum Seller OpenAPI (api-seller.uzum.uz)."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Literal, Optional
from uuid import UUID

from datetime import date

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.routes.imports import import_uzum_api_sync
from app.services.uzum_export import (
    UzumRateLimitError,
    build_report,
    build_xlsx_bytes,
    report_metadata,
)
from app.services.uzum_time import timezone_metadata

logger = logging.getLogger(__name__)
router = APIRouter()

UZUM_HOST = "https://api-seller.uzum.uz"
OPENAPI_SPEC_URL = f"{UZUM_HOST}/api/seller-openapi/swagger/api-docs"
API_BASE_URL = f"{UZUM_HOST}/api/seller-openapi"
REQUEST_TIMEOUT = 30

# From Uzum OpenAPI: Authorization header, token WITHOUT "Bearer " prefix.
DEFAULT_AUTH_MODE = "authorization_raw"
AuthMode = Literal["bearer", "authorization_raw", "x-api-key", "x-api-key-alt", "api-key"]


def _warnings_response_header(warnings: list[str]) -> str:
    """HTTP headers must be latin-1; encode UTF-8 warnings as base64 JSON."""
    payload = json.dumps(warnings, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def _normalize_api_key(raw: str) -> str:
    key = raw.strip()
    if key.lower().startswith("bearer "):
        return key[7:].strip()
    return key


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


def _validate_api_key(api_key: str) -> tuple[bool, Optional[str], Optional[int]]:
    """Probe a lightweight GET endpoint to verify the seller token."""
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


class OpenApiExploreBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)


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
    api_key = _normalize_api_key(body.api_key)
    spec = _load_openapi_spec()
    key_valid, key_error, key_status = _validate_api_key(api_key)
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
    api_key = _normalize_api_key(body.api_key)
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
    api_key = _normalize_api_key(body.api_key)
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
    except UzumRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
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
    api_key = _normalize_api_key(body.api_key)
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
    except UzumRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "file_name": filename,
        "row_count": len(rows),
        "columns": [{"name": c.name, "mapped": c.mapped} for c in columns],
        "rows": rows[:limit],
        "warnings": warnings,
        **timezone_metadata(),
    }


UZUM_SYNC_REPORT_TYPES = ("inventory_old", "sales", "expenses", "storage")


class UzumSyncBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)
    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD, default: Jan 1 current year")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD, default: today")


@router.post("/uzum-seller/reports/sync")
def sync_uzum_reports_to_service(
    body: UzumSyncBody,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Fetch four Uzum reports (YTD by default) and import them into the service."""
    api_key = _normalize_api_key(body.api_key)
    today = date.today()
    date_from = body.date_from or f"{today.year}-01-01"
    date_to = body.date_to or today.isoformat()

    key_valid, key_error, _ = _validate_api_key(api_key)
    if not key_valid:
        raise HTTPException(status_code=401, detail=key_error or "Invalid Uzum API key")

    files: dict[str, bytes] = {}
    file_names: dict[str, str] = {}
    warnings: list[str] = []

    for report_type in UZUM_SYNC_REPORT_TYPES:
        try:
            kwargs: dict[str, Any] = {}
            if report_type in ("sales", "expenses"):
                kwargs["date_from"] = date_from
                kwargs["date_to"] = date_to
            columns, rows, filename, report_warnings = build_report(
                report_type,
                api_key,
                **kwargs,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UzumRateLimitError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        files[report_type] = build_xlsx_bytes(report_type, columns, rows)
        file_names[report_type] = filename
        warnings.extend(report_warnings)

    try:
        result = import_uzum_api_sync(db, user_id, files, file_names)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Uzum sync import failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if warnings:
        logger.info("Uzum sync warnings: %s", warnings)

    return {
        **result,
        "date_from": date_from,
        "date_to": date_to,
        "warnings": warnings,
        **timezone_metadata(),
    }
