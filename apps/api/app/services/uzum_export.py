"""Build import-compatible XLSX reports from Uzum Seller API."""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import requests
from openpyxl import Workbook
from openpyxl.styles import Font

from app.services.uzum_time import (
    calendar_date_to_epoch_ms,
    format_datetime,
    last_n_days_range_ms,
    normalize_epoch_ms,
    parse_to_epoch_ms,
    timezone_metadata,
)
from app.utils.column_mappings import (
    CANONICAL_EXPENSES,
    CANONICAL_LEFTOUT_OLD,
    CANONICAL_SALES,
    CANONICAL_STORAGE,
)

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api-seller.uzum.uz/api/seller-openapi"
REQUEST_TIMEOUT = 45
PAGE_SIZE = 100
PRODUCT_PAGE_SIZE = 100
MAX_PAGES = 200
# Uzum rate-limits seller API; space out calls and retry on 429.
MIN_REQUEST_INTERVAL_SEC = 0.5
MAX_RETRIES_RATE_LIMIT = 6
MAX_BACKOFF_SEC = 45.0
PAUSE_BETWEEN_SHOPS_SEC = 0.75
SALES_LOOKBACK_DAYS = 15

FINANCE_ORDER_STATUSES = [
    "TO_WITHDRAW",
    "PROCESSING",
    "CANCELED",
    "PARTIALLY_CANCELLED",
]

SALES_STATUS_RU = {
    "TO_WITHDRAW": "К выводу",
    "PROCESSING": "В обработке",
    "CANCELED": "Отменен",
    "PARTIALLY_CANCELLED": "Частично отменен",
}

EXPENSE_STATUS_RU = {
    "CREATED": "Создан",
    "REFUNDED": "Возвращен",
    "CONFIRMED": "Оплачено",
    "CANCELED": "Отменен",
}

EXPENSE_TYPE_RU = {
    "OUTCOME": "Оплата",
    "INCOME": "Возврат",
}

SHEET_NAMES = {
    "sales": "Отчет по продажам",
    "expenses": "Отчет по услугам",
    "storage": "Отчет по хранению",
    "inventory_old": "Остатки (старый)",
}

FILE_NAMES = {
    "sales": "sells-report_uzum-api.xlsx",
    "expenses": "expenses-report_uzum-api.xlsx",
    "storage": "seller-storage-report_uzum-api.xlsx",
    "inventory_old": "left-out-report_uzum-api.xlsx",
}


@dataclass(frozen=True)
class ExportColumn:
    name: str
    mapped: bool


class ShopUnavailableError(RuntimeError):
    """Uzum rejected a shopId (forbidden-001 / Shop is not available)."""


class UzumRateLimitError(RuntimeError):
    """Uzum returned HTTP 429 (too many requests)."""


def _errors_indicate_unavailable_shop(errors: Any) -> bool:
    if not isinstance(errors, list):
        return False
    for entry in errors:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code") or "")
        message = str(entry.get("message") or "")
        if code == "forbidden-001" or "not available" in message.lower():
            return True
    return False


def _detail_is_shop_unavailable(detail: Any) -> bool:
    if _errors_indicate_unavailable_shop(detail):
        return True
    if isinstance(detail, dict):
        return _errors_indicate_unavailable_shop(detail.get("errors"))
    return False


def _format_uzum_error(status: int, detail: Any) -> str:
    if isinstance(detail, dict):
        errors = detail.get("errors")
        if errors:
            return f"Uzum API {status}: {errors}"
        if detail.get("message"):
            return f"Uzum API {status}: {detail['message']}"
        if detail.get("error"):
            return f"Uzum API {status}: {detail['error']}"
    if isinstance(detail, list):
        return f"Uzum API {status}: {detail}"
    return f"Uzum API {status}: {detail}"


def _check_envelope_errors(data: Any) -> None:
    if not isinstance(data, dict):
        return
    errors = data.get("errors")
    if errors:
        if _errors_indicate_unavailable_shop(errors):
            raise ShopUnavailableError(f"Uzum API: {errors}")
        raise RuntimeError(f"Uzum API: {errors}")


def _flatten_order_items(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unwrap ProductGroupedSellerItem (group=true) into flat line items."""
    flat: list[dict[str, Any]] = []
    for item in batch:
        nested = item.get("items")
        if isinstance(nested, list) and nested:
            parent_title = item.get("productTitle") or ""
            parent_shop = item.get("shopId")
            for sub in nested:
                if not isinstance(sub, dict):
                    continue
                row = dict(sub)
                if not row.get("productTitle"):
                    row["productTitle"] = parent_title
                if row.get("shopId") is None:
                    row["shopId"] = parent_shop
                flat.append(row)
        else:
            flat.append(item)
    return flat


def _shop_label(shop_names: dict[int, str], shop_id: Any) -> str:
    if shop_id is None:
        return ""
    try:
        return shop_names.get(int(shop_id), "")
    except (TypeError, ValueError):
        return ""


def _order_item_timestamp_ms(item: dict[str, Any]) -> Optional[int]:
    for key in ("date", "dateIssued"):
        ts = normalize_epoch_ms(item.get(key))
        if ts is not None:
            return ts
    return None


def _payment_timestamp_ms(payment: dict[str, Any]) -> Optional[int]:
    for key in ("dateService", "dateCreated"):
        ts = parse_to_epoch_ms(payment.get(key))
        if ts is not None:
            return ts
    return None


def _in_date_range(
    ts_ms: Optional[int],
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
) -> bool:
    if date_from_ms is None and date_to_ms is None:
        return True
    if ts_ms is None:
        return False
    if date_from_ms is not None and ts_ms < date_from_ms:
        return False
    if date_to_ms is not None and ts_ms > date_to_ms:
        return False
    return True


def _filter_by_date_range(
    records: list[dict[str, Any]],
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
    ts_getter: Callable[[dict[str, Any]], Optional[int]],
) -> list[dict[str, Any]]:
    if date_from_ms is None and date_to_ms is None:
        return records
    return [
        record
        for record in records
        if _in_date_range(ts_getter(record), date_from_ms, date_to_ms)
    ]


def _apply_date_query_params(
    params: dict[str, Any],
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
    *,
    unit_ms: bool = True,
) -> None:
    if date_from_ms is not None:
        params["dateFrom"] = date_from_ms if unit_ms else date_from_ms // 1000
    if date_to_ms is not None:
        params["dateTo"] = date_to_ms if unit_ms else date_to_ms // 1000


def _format_barcode(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _barcode_keys(barcode: str) -> list[str]:
    if not barcode:
        return []
    keys = [barcode]
    stripped = barcode.lstrip("0")
    if stripped and stripped not in keys:
        keys.append(stripped)
    return keys


def _format_dimensional_group(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("name", "code", "title", "label"):
            part = value.get(key)
            if part:
                return str(part)
        return ""
    return str(value)


def _pstorage_label(value: Any) -> str:
    if value is True:
        return "Платное хранение"
    if value is False:
        return "Бесплатное"
    return ""


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_turnover_days(stock_qty: Any, avg_daily_sales: Any) -> Any:
    """Остаток / среднесуточные продажи (дней), как в left-out-report."""
    stock = _safe_float(stock_qty)
    avg = _safe_float(avg_daily_sales)
    if stock is None or avg is None or avg <= 0:
        return ""
    days = stock / avg
    if days >= 100:
        return int(round(days))
    return round(days, 1)


def _format_sales_rate(value: float) -> Any:
    if value <= 0:
        return ""
    if abs(value - round(value)) < 0.01:
        return int(round(value))
    return round(value, 2)


@dataclass
class SkuCatalogEntry:
    shop_id: int
    sku_id: Optional[int]
    product_id: Optional[int]
    barcode: str
    category: str
    dimensional_group: str
    purchase_price: Any
    sell_price: Any
    paid_storage_price_item: Any
    paid_storage_amount: Any
    avg_daily_sales: Any
    quantity_active: Any
    quantity_pending: Any
    pstorage: Optional[bool]
    sku_title: str
    sku_full_title: str
    article: str
    seller_item_code: str
    product_title: str


@dataclass
class ProductCatalogIndex:
    by_sku_id: dict[tuple[int, int], SkuCatalogEntry] = field(default_factory=dict)
    by_sku_id_global: dict[int, SkuCatalogEntry] = field(default_factory=dict)
    by_product_id: dict[tuple[int, int], SkuCatalogEntry] = field(default_factory=dict)
    by_barcode: dict[str, list[SkuCatalogEntry]] = field(default_factory=dict)
    skus_by_product: dict[tuple[int, int], list[SkuCatalogEntry]] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> ProductCatalogIndex:
        return cls()

    @property
    def size(self) -> int:
        return len(self.by_sku_id_global)

    def add_shop_products(self, shop_id: int, products: list[dict[str, Any]]) -> None:
        for product in products:
            if not isinstance(product, dict):
                continue
            category = str(product.get("category") or "")
            product_id_raw = product.get("productId")
            product_id: Optional[int] = None
            if product_id_raw is not None:
                try:
                    product_id = int(product_id_raw)
                except (TypeError, ValueError):
                    product_id = None
            product_title = str(product.get("title") or product.get("skuTitle") or "")
            sku_list = product.get("skuList") or []
            if not isinstance(sku_list, list):
                continue
            for sku in sku_list:
                if not isinstance(sku, dict):
                    continue
                sku_id_raw = sku.get("skuId")
                sku_id: Optional[int] = None
                if sku_id_raw is not None:
                    try:
                        sku_id = int(sku_id_raw)
                    except (TypeError, ValueError):
                        sku_id = None
                barcode = _format_barcode(sku.get("barcode"))
                entry = SkuCatalogEntry(
                    shop_id=shop_id,
                    sku_id=sku_id,
                    product_id=product_id,
                    barcode=barcode,
                    category=category,
                    dimensional_group=_format_dimensional_group(
                        sku.get("dimensionalGroup") or sku.get("paidStorageDimensionalGroup")
                    ),
                    purchase_price=sku.get("purchasePrice"),
                    sell_price=sku.get("price"),
                    paid_storage_price_item=sku.get("paidStoragePriceItem"),
                    paid_storage_amount=sku.get("paidStorageAmount"),
                    avg_daily_sales=sku.get("avgdsales"),
                    quantity_active=sku.get("quantityActive"),
                    quantity_pending=sku.get("quantityPending"),
                    pstorage=sku.get("pstorage"),
                    sku_title=str(sku.get("skuTitle") or ""),
                    sku_full_title=str(sku.get("skuFullTitle") or ""),
                    article=str(sku.get("article") or ""),
                    seller_item_code=str(sku.get("sellerItemCode") or ""),
                    product_title=str(sku.get("productTitle") or product_title),
                )
                if sku_id is not None:
                    self.by_sku_id[(shop_id, sku_id)] = entry
                    self.by_sku_id_global[sku_id] = entry
                if product_id is not None:
                    key = (shop_id, product_id)
                    self.by_product_id.setdefault(key, entry)
                    self.skus_by_product.setdefault(key, []).append(entry)
                for key in _barcode_keys(barcode):
                    self.by_barcode.setdefault(key, []).append(entry)

    def lookup_order_item(self, item: dict[str, Any]) -> Optional[SkuCatalogEntry]:
        shop_raw = item.get("shopId")
        if shop_raw is None:
            return self._lookup_without_shop(item)
        try:
            shop_id = int(shop_raw)
        except (TypeError, ValueError):
            return self._lookup_without_shop(item)

        sku_raw = item.get("skuId")
        if sku_raw is not None:
            try:
                entry = self.by_sku_id.get((shop_id, int(sku_raw)))
                if entry:
                    return entry
            except (TypeError, ValueError):
                pass

        product_raw = item.get("productId")
        product_id: Optional[int] = None
        if product_raw is not None:
            try:
                product_id = int(product_raw)
            except (TypeError, ValueError):
                product_id = None

        if product_id is not None:
            key = (shop_id, product_id)
            sku_title = str(item.get("skuTitle") or item.get("skuCharTitle") or "")
            for candidate in self.skus_by_product.get(key, []):
                if sku_title and (
                    sku_title == candidate.sku_title
                    or sku_title in candidate.sku_title
                    or candidate.sku_title in sku_title
                ):
                    return candidate
            entry = self.by_product_id.get(key)
            if entry:
                return entry

        return self._lookup_without_shop(item)

    def _lookup_without_shop(self, item: dict[str, Any]) -> Optional[SkuCatalogEntry]:
        sku_raw = item.get("skuId")
        if sku_raw is not None:
            try:
                entry = self.by_sku_id_global.get(int(sku_raw))
                if entry:
                    return entry
            except (TypeError, ValueError):
                pass
        for key in _barcode_keys(_format_barcode(item.get("barcode"))):
            entries = self.by_barcode.get(key)
            if entries:
                return entries[0]
        return None

    def lookup_stock_row(self, stock: dict[str, Any]) -> Optional[SkuCatalogEntry]:
        sku_raw = stock.get("skuId")
        if sku_raw is not None:
            try:
                entry = self.by_sku_id_global.get(int(sku_raw))
                if entry:
                    return entry
            except (TypeError, ValueError):
                pass
        for key in _barcode_keys(_format_barcode(stock.get("barcode"))):
            entries = self.by_barcode.get(key)
            if entries:
                return entries[0]
        return None


class UzumApiClient:
    def __init__(self, api_key: str):
        self._headers = {
            "Authorization": api_key,
            "Accept": "application/json",
            "Accept-Language": "ru-RU",
        }
        self.warnings: list[str] = []
        self._last_request_at: float = 0.0
        self._shops_cache: Optional[list[dict[str, Any]]] = None

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_REQUEST_INTERVAL_SEC:
            time.sleep(MIN_REQUEST_INTERVAL_SEC - elapsed)

    def _retry_after_seconds(self, response: requests.Response, attempt: int) -> float:
        raw = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if raw:
            try:
                return min(float(raw), MAX_BACKOFF_SEC)
            except ValueError:
                pass
        return min(2.0 * (2**attempt), MAX_BACKOFF_SEC)

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{API_BASE_URL.rstrip('/')}{path if path.startswith('/') else '/' + path}"
        last_error: Optional[RuntimeError] = None

        for attempt in range(MAX_RETRIES_RATE_LIMIT + 1):
            self._throttle()
            response = requests.get(
                url,
                headers=self._headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            self._last_request_at = time.monotonic()

            if response.status_code == 429:
                wait_sec = self._retry_after_seconds(response, attempt)
                logger.warning(
                    "Uzum API 429 on %s, retry %s/%s after %.1fs",
                    path,
                    attempt + 1,
                    MAX_RETRIES_RATE_LIMIT,
                    wait_sec,
                )
                if attempt >= MAX_RETRIES_RATE_LIMIT:
                    raise UzumRateLimitError(
                        "Uzum API временно ограничил частоту запросов (429). "
                        "Подождите 1–2 минуты и повторите выгрузку."
                    )
                time.sleep(wait_sec)
                continue

            if response.status_code >= 400:
                try:
                    detail = response.json()
                except ValueError:
                    detail = response.text
                if _detail_is_shop_unavailable(detail):
                    raise ShopUnavailableError(_format_uzum_error(response.status_code, detail))
                last_error = RuntimeError(_format_uzum_error(response.status_code, detail))
                break

            if not response.content:
                return None
            data = response.json()
            _check_envelope_errors(data)
            return data

        if last_error:
            raise last_error
        raise UzumRateLimitError(
            "Uzum API временно ограничил частоту запросов (429). "
            "Подождите 1–2 минуты и повторите выгрузку."
        )

    def list_shops(self) -> list[dict[str, Any]]:
        if self._shops_cache is not None:
            return self._shops_cache
        data = self.get("/v1/shops")
        if isinstance(data, list):
            self._shops_cache = data
            return data
        self._shops_cache = []
        return []

    def list_shop_ids(self) -> list[int]:
        ids: list[int] = []
        for shop in self.list_shops():
            raw = shop.get("id")
            if raw is None:
                continue
            try:
                ids.append(int(raw))
            except (TypeError, ValueError):
                continue
        return ids

    def resolve_shop_ids(self, shop_ids: Optional[list[int]] = None) -> list[int]:
        if shop_ids:
            return shop_ids
        resolved = self.list_shop_ids()
        if not resolved:
            raise RuntimeError(
                "Не найдены магазины в Uzum API (/v1/shops). Проверьте API-ключ и права доступа."
            )
        return resolved

    def _fetch_orders_for_shop(
        self,
        shop_id: int,
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 0
        while page < MAX_PAGES:
            params: dict[str, Any] = {
                "page": page,
                "size": PAGE_SIZE,
                "group": False,
                "shopIds": [shop_id],
                "statuses": FINANCE_ORDER_STATUSES,
            }
            _apply_date_query_params(params, date_from_ms, date_to_ms, unit_ms=unit_ms)
            data = self.get("/v1/finance/orders", params)
            raw_batch = (data or {}).get("orderItems") or []
            batch = _flatten_order_items(raw_batch)
            if not batch:
                break
            items.extend(batch)
            total = (data or {}).get("totalElements")
            if total is not None and len(items) >= int(total):
                break
            if len(raw_batch) < PAGE_SIZE:
                break
            page += 1
        return items

    def _fetch_expenses_for_shop(
        self,
        shop_id: int,
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        payments: list[dict[str, Any]] = []
        page = 0
        while page < MAX_PAGES:
            params: dict[str, Any] = {
                "page": page,
                "size": PAGE_SIZE,
                "shopIds": [shop_id],
            }
            _apply_date_query_params(params, date_from_ms, date_to_ms, unit_ms=unit_ms)
            data = self.get("/v1/finance/expenses", params)
            payload = (data or {}).get("payload") or data or {}
            if isinstance(payload, dict):
                errors = payload.get("errors")
                if errors:
                    if _errors_indicate_unavailable_shop(errors):
                        raise ShopUnavailableError(f"Uzum API: {errors}")
                    raise RuntimeError(f"Uzum API: {errors}")
            batch: list[dict[str, Any]] = []
            if isinstance(payload, dict):
                batch = payload.get("payments") or []
            if not batch:
                break
            payments.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1
        return payments

    def _fetch_orders_bulk(
        self,
        shop_ids: list[int],
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        """One paginated stream for all available shops (fewer HTTP calls)."""
        items: list[dict[str, Any]] = []
        page = 0
        while page < MAX_PAGES:
            params: dict[str, Any] = {
                "page": page,
                "size": PAGE_SIZE,
                "group": False,
                "shopIds": shop_ids,
                "statuses": FINANCE_ORDER_STATUSES,
            }
            _apply_date_query_params(params, date_from_ms, date_to_ms, unit_ms=unit_ms)
            data = self.get("/v1/finance/orders", params)
            raw_batch = (data or {}).get("orderItems") or []
            batch = _flatten_order_items(raw_batch)
            if not batch:
                break
            items.extend(batch)
            total = (data or {}).get("totalElements")
            if total is not None and len(items) >= int(total):
                break
            if len(raw_batch) < PAGE_SIZE:
                break
            page += 1
        return items

    def _fetch_expenses_bulk(
        self,
        shop_ids: list[int],
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        payments: list[dict[str, Any]] = []
        page = 0
        while page < MAX_PAGES:
            params: dict[str, Any] = {
                "page": page,
                "size": PAGE_SIZE,
                "shopIds": shop_ids,
            }
            _apply_date_query_params(params, date_from_ms, date_to_ms, unit_ms=unit_ms)
            data = self.get("/v1/finance/expenses", params)
            payload = (data or {}).get("payload") or data or {}
            if isinstance(payload, dict):
                errors = payload.get("errors")
                if errors:
                    if _errors_indicate_unavailable_shop(errors):
                        raise ShopUnavailableError(f"Uzum API: {errors}")
                    raise RuntimeError(f"Uzum API: {errors}")
            batch: list[dict[str, Any]] = []
            if isinstance(payload, dict):
                batch = payload.get("payments") or []
            if not batch:
                break
            payments.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1
        return payments

    def _probe_shop_for_orders(self, shop_id: int) -> bool:
        params: dict[str, Any] = {
            "page": 0,
            "size": 1,
            "group": False,
            "shopIds": [shop_id],
            "statuses": FINANCE_ORDER_STATUSES,
        }
        try:
            self.get("/v1/finance/orders", params)
            return True
        except ShopUnavailableError:
            return False

    def _probe_shop_for_expenses(self, shop_id: int) -> bool:
        params: dict[str, Any] = {"page": 0, "size": 1, "shopIds": [shop_id]}
        try:
            self.get("/v1/finance/expenses", params)
            return True
        except ShopUnavailableError:
            return False

    def _fetch_orders_for_shops(
        self,
        shop_ids: list[int],
        names: dict[int, str],
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        if len(shop_ids) == 1:
            return self._fetch_orders_for_shop(
                shop_ids[0], date_from_ms, date_to_ms, unit_ms=unit_ms
            )
        try:
            return self._fetch_orders_bulk(
                shop_ids, date_from_ms, date_to_ms, unit_ms=unit_ms
            )
        except ShopUnavailableError:
            self.warnings.append(
                "Сводная выгрузка недоступна, загружаем магазины по одному (медленнее)."
            )
            return self._collect_per_shop(
                shop_ids,
                names,
                lambda sid: self._fetch_orders_for_shop(
                    sid, date_from_ms, date_to_ms, unit_ms=unit_ms
                ),
            )

    def _fetch_expenses_for_shops(
        self,
        shop_ids: list[int],
        names: dict[int, str],
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        *,
        unit_ms: bool = True,
    ) -> list[dict[str, Any]]:
        if len(shop_ids) == 1:
            return self._fetch_expenses_for_shop(
                shop_ids[0], date_from_ms, date_to_ms, unit_ms=unit_ms
            )
        try:
            return self._fetch_expenses_bulk(
                shop_ids, date_from_ms, date_to_ms, unit_ms=unit_ms
            )
        except ShopUnavailableError:
            self.warnings.append(
                "Сводная выгрузка недоступна, загружаем магазины по одному (медленнее)."
            )
            return self._collect_per_shop(
                shop_ids,
                names,
                lambda sid: self._fetch_expenses_for_shop(
                    sid, date_from_ms, date_to_ms, unit_ms=unit_ms
                ),
            )

    def _fetch_dated_records(
        self,
        available: list[int],
        names: dict[int, str],
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        fetcher: Callable[..., list[dict[str, Any]]],
        filter_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        label: str,
    ) -> list[dict[str, Any]]:
        items = fetcher(available, names, date_from_ms, date_to_ms, unit_ms=True)
        if items or (date_from_ms is None and date_to_ms is None):
            return items

        items = fetcher(available, names, date_from_ms, date_to_ms, unit_ms=False)
        if items:
            self.warnings.append(
                f"{label}: API принял границы периода в секундах (автоподбор формата)."
            )
            return items

        raw = fetcher(available, names, None, None, unit_ms=True)
        if not raw:
            return []

        filtered = filter_fn(raw)
        if filtered:
            self.warnings.append(
                f"{label}: серверный фильтр дат не вернул строки; "
                "применена локальная фильтрация по дате записи."
            )
            return filtered

        self.warnings.append(
            f"{label}: в API найдено {len(raw)} записей, но ни одна не попадает "
            "в выбранный период. Расширьте диапазон дат."
        )
        return []

    def _filter_available_shops(
        self,
        shop_ids: list[int],
        shop_names: dict[int, str],
        probe: Callable[[int], bool],
    ) -> list[int]:
        available: list[int] = []
        unavailable: list[str] = []
        for shop_id in shop_ids:
            label = shop_names.get(shop_id) or f"ID {shop_id}"
            if probe(shop_id):
                available.append(shop_id)
            else:
                unavailable.append(label)
            if PAUSE_BETWEEN_SHOPS_SEC > 0:
                time.sleep(PAUSE_BETWEEN_SHOPS_SEC)
        if unavailable:
            self.warnings.append(
                "Пропущены недоступные магазины (нет доступа в финансовом API): "
                + ", ".join(unavailable)
            )
        return available

    def _collect_per_shop(
        self,
        shop_ids: list[int],
        shop_names: dict[int, str],
        fetcher: Callable[[int], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        combined: list[dict[str, Any]] = []
        unavailable: list[str] = []
        for shop_id in shop_ids:
            label = shop_names.get(shop_id) or f"ID {shop_id}"
            try:
                combined.extend(fetcher(shop_id))
            except ShopUnavailableError:
                unavailable.append(label)
                continue
            finally:
                if PAUSE_BETWEEN_SHOPS_SEC > 0:
                    time.sleep(PAUSE_BETWEEN_SHOPS_SEC)
        if unavailable:
            self.warnings.append(
                "Пропущены недоступные магазины (нет доступа в финансовом API): "
                + ", ".join(unavailable)
            )
        return combined

    def fetch_finance_orders(
        self,
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        shop_ids: list[int],
        shop_names: Optional[dict[int, str]] = None,
    ) -> list[dict[str, Any]]:
        if not shop_ids:
            raise RuntimeError("Для отчёта по продажам нужен хотя бы один магазин (shopIds).")

        names = shop_names or {sid: f"ID {sid}" for sid in shop_ids}
        available = self._filter_available_shops(
            shop_ids,
            names,
            self._probe_shop_for_orders,
        )
        if not available:
            raise RuntimeError(
                "Нет доступных магазинов для отчёта по продажам. "
                + (self.warnings[-1] if self.warnings else "")
            )

        return self._fetch_dated_records(
            available,
            names,
            date_from_ms,
            date_to_ms,
            self._fetch_orders_for_shops,
            lambda rows: _filter_by_date_range(
                rows, date_from_ms, date_to_ms, _order_item_timestamp_ms
            ),
            "Продажи",
        )

    def fetch_finance_expenses(
        self,
        date_from_ms: Optional[int],
        date_to_ms: Optional[int],
        shop_ids: list[int],
        shop_names: Optional[dict[int, str]] = None,
    ) -> list[dict[str, Any]]:
        if not shop_ids:
            raise RuntimeError("Для отчёта по услугам нужен хотя бы один магазин.")

        names = shop_names or {sid: f"ID {sid}" for sid in shop_ids}
        available = self._filter_available_shops(
            shop_ids,
            names,
            self._probe_shop_for_expenses,
        )
        if not available:
            raise RuntimeError(
                "Нет доступных магазинов для отчёта по услугам. "
                + (self.warnings[-1] if self.warnings else "")
            )

        return self._fetch_dated_records(
            available,
            names,
            date_from_ms,
            date_to_ms,
            self._fetch_expenses_for_shops,
            lambda rows: _filter_by_date_range(
                rows, date_from_ms, date_to_ms, _payment_timestamp_ms
            ),
            "Услуги",
        )

    def fetch_sku_stocks(self) -> list[dict[str, Any]]:
        data = self.get("/v2/fbs/sku/stocks")
        payload = (data or {}).get("payload") or {}
        return payload.get("skuAmountList") or []

    def fetch_product_catalog_index(self, shop_ids: list[int]) -> ProductCatalogIndex:
        index = ProductCatalogIndex.empty()
        if not shop_ids:
            return index
        for shop_id in shop_ids:
            page = 0
            loaded = 0
            while page < MAX_PAGES:
                data = self.get(
                    f"/v1/product/shop/{shop_id}",
                    {
                        "page": page,
                        "size": PRODUCT_PAGE_SIZE,
                        "filter": "ALL",
                    },
                )
                products = (data or {}).get("productList") or []
                if not products:
                    break
                index.add_shop_products(shop_id, products)
                loaded += len(products)
                total = (data or {}).get("totalProductsAmount")
                if total is not None and loaded >= int(total):
                    break
                if len(products) < PRODUCT_PAGE_SIZE:
                    break
                page += 1
            if PAUSE_BETWEEN_SHOPS_SEC > 0:
                time.sleep(PAUSE_BETWEEN_SHOPS_SEC)
        if index.size:
            self.warnings.append(
                "Часть колонок дополнена из каталога товаров Uzum (/v1/product/shop)."
            )
        return index

    def _accumulate_item_qty(
        self,
        item: dict[str, Any],
        catalog: ProductCatalogIndex,
        totals: dict[int, int],
    ) -> None:
        cat = catalog.lookup_order_item(item)
        sku_id: Optional[int] = None
        if cat and cat.sku_id is not None:
            sku_id = cat.sku_id
        else:
            raw = item.get("skuId")
            if raw is not None:
                try:
                    sku_id = int(raw)
                except (TypeError, ValueError):
                    sku_id = None
        if sku_id is None:
            return
        try:
            qty = int(item.get("amount") or 1)
        except (TypeError, ValueError):
            qty = 1
        if qty < 0:
            qty = 0
        totals[sku_id] = totals.get(sku_id, 0) + qty

    def _fetch_scheme_order_qty_totals(
        self,
        shop_ids: list[int],
        date_from_ms: int,
        date_to_ms: int,
        scheme: str,
        catalog: ProductCatalogIndex,
    ) -> dict[int, int]:
        totals: dict[int, int] = {}
        page = 0
        while page < MAX_PAGES:
            params: dict[str, Any] = {
                "shopIds": shop_ids,
                "page": page,
                "size": PAGE_SIZE,
                "status": "COMPLETED",
                "dateFrom": date_from_ms,
                "dateTo": date_to_ms,
            }
            data = self.get("/v2/fbs/orders", params)
            payload = (data or {}).get("payload") or {}
            orders = payload.get("orders") or []
            if not orders:
                break
            for order in orders:
                if not isinstance(order, dict):
                    continue
                if str(order.get("scheme") or "").upper() != scheme.upper():
                    continue
                for item in order.get("orderItems") or []:
                    if isinstance(item, dict):
                        self._accumulate_item_qty(item, catalog, totals)
            total_amount = payload.get("totalAmount")
            if total_amount is not None and (page + 1) * PAGE_SIZE >= int(total_amount):
                break
            if len(orders) < PAGE_SIZE:
                break
            page += 1
        return totals

    def fetch_avg_daily_sales_15d_by_sku(
        self,
        shop_ids: list[int],
        catalog: ProductCatalogIndex,
        shop_names: dict[int, str],
    ) -> dict[int, float]:
        """Среднесуточные продажи за 15 дней по skuId (приоритет — заказы FBO)."""
        date_from_ms, date_to_ms = last_n_days_range_ms(SALES_LOOKBACK_DAYS)
        totals = self._fetch_scheme_order_qty_totals(
            shop_ids, date_from_ms, date_to_ms, "FBO", catalog
        )
        if not totals:
            items = self.fetch_finance_orders(date_from_ms, date_to_ms, shop_ids, shop_names)
            for item in items:
                self._accumulate_item_qty(item, catalog, totals)
            if totals:
                self.warnings.append(
                    f"«Среднесуточные продажи FBO за {SALES_LOOKBACK_DAYS} дней»: "
                    "заказы FBO в API не найдены, использованы все финансовые продажи за период."
                )
        return {
            sku_id: total / SALES_LOOKBACK_DAYS
            for sku_id, total in totals.items()
            if total > 0
        }


def _sales_sku_label(item: dict[str, Any], cat: Optional[SkuCatalogEntry]) -> str:
    """Human-readable seller SKU (e.g. SKLPTR-SLIP-БЕЛЫЙ-L), not numeric skuId."""
    if cat:
        for candidate in (
            cat.article,
            cat.seller_item_code,
            cat.sku_full_title,
            cat.sku_title,
        ):
            if candidate:
                return candidate
    for key in ("skuCharValue", "skuCharTitle", "skuTitle"):
        value = item.get(key)
        if value:
            return str(value)
    if cat and cat.sku_title:
        return cat.sku_title
    return ""


def _sales_money_fields(item: dict[str, Any]) -> tuple[Any, Any, Any, Any, Any]:
    # Цена — sellerPrice/sellPrice; выручка 0 при возврате; net = выручка − комиссия − логистика.
    price = item.get("sellerPrice")
    if price is None:
        price = item.get("sellPrice")

    returns_raw = item.get("amountReturns")
    try:
        has_return = int(returns_raw or 0) > 0
    except (TypeError, ValueError):
        has_return = False

    revenue: Any = 0 if has_return else price

    def _as_int(value: Any) -> int:
        if value is None or value == "":
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    revenue_net = _as_int(revenue) - _as_int(item.get("commission")) - _as_int(
        item.get("logisticDeliveryFee")
    )
    return price, revenue, revenue_net, item.get("commission"), item.get("logisticDeliveryFee")


def _build_sales_rows(
    items: list[dict[str, Any]],
    shop_names: dict[int, str],
    catalog: Optional[ProductCatalogIndex] = None,
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    columns = [
        ExportColumn("Статус", True),
        ExportColumn("Дата создания", True),
        ExportColumn("Дата получения", True),
        ExportColumn("№ заказа", True),
        ExportColumn("Штрихкод", True),
        ExportColumn("SKU", True),
        ExportColumn("Наименование", True),
        ExportColumn("Категория", True),
        ExportColumn("Количество", True),
        ExportColumn("Возвраты", True),
        ExportColumn("Выручка (сумы)", True),
        ExportColumn("Выручка с вычетом комиссии и логистики (сумы)", True),
        ExportColumn("Комиссия маркетплейса (сумы)", True),
        ExportColumn("Цена (сумы)", True),
        ExportColumn("Промокод (сумы)", False),
        ExportColumn("Себестоимость (сумы)", True),
        ExportColumn("Логистический сбор", True),
    ]
    assert {c.name for c in columns} == CANONICAL_SALES

    rows: list[dict[str, Any]] = []
    for item in items:
        shop_id = item.get("shopId")
        cat = catalog.lookup_order_item(item) if catalog else None
        price, revenue, revenue_net, commission, logistics = _sales_money_fields(item)
        rows.append(
            {
                "Статус": SALES_STATUS_RU.get(str(item.get("status") or ""), item.get("status") or ""),
                "Дата создания": format_datetime(item.get("date")),
                "Дата получения": format_datetime(item.get("dateIssued")),
                "№ заказа": item.get("orderId"),
                "Штрихкод": (cat.barcode if cat else "") or _format_barcode(item.get("barcode")),
                "SKU": _sales_sku_label(item, cat),
                "Наименование": item.get("productTitle") or item.get("skuTitle") or (cat.product_title if cat else ""),
                "Категория": (cat.category if cat else ""),
                "Количество": item.get("amount"),
                "Возвраты": item.get("amountReturns"),
                "Выручка (сумы)": revenue,
                "Выручка с вычетом комиссии и логистики (сумы)": revenue_net,
                "Комиссия маркетплейса (сумы)": commission,
                "Цена (сумы)": price,
                "Промокод (сумы)": "",
                "Себестоимость (сумы)": item.get("purchasePrice")
                if item.get("purchasePrice") is not None
                else (cat.purchase_price if cat else None),
                "Логистический сбор": item.get("logisticDeliveryFee"),
                "_shop": _shop_label(shop_names, shop_id),
            }
        )
    return columns, rows


def _build_expenses_rows(payments: list[dict[str, Any]], shop_names: dict[int, str]) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    columns = [
        ExportColumn("Источник", True),
        ExportColumn("Услуга", True),
        ExportColumn("Статус", True),
        ExportColumn("ID операции", True),
        ExportColumn("Дата списания", True),
        ExportColumn("Стоимость (сумы)", True),
        ExportColumn("Количество", True),
        ExportColumn("Сумма (сумы)", True),
        ExportColumn("Тип операции", True),
    ]
    assert {c.name for c in columns} == CANONICAL_EXPENSES

    rows: list[dict[str, Any]] = []
    for p in payments:
        shop_id = p.get("shopId")
        rows.append(
            {
                "Источник": p.get("source") or "",
                "Услуга": p.get("name") or "",
                "Статус": EXPENSE_STATUS_RU.get(str(p.get("status") or ""), p.get("status") or ""),
                "ID операции": p.get("id") if p.get("id") is not None else p.get("externalId"),
                "Дата списания": format_datetime(p.get("dateService") or p.get("dateCreated")),
                "Стоимость (сумы)": p.get("paymentPrice"),
                "Количество": p.get("amount"),
                "Сумма (сумы)": p.get("paymentPrice"),
                "Тип операции": EXPENSE_TYPE_RU.get(str(p.get("type") or ""), p.get("type") or ""),
                "_shop": _shop_label(shop_names, shop_id),
            }
        )
    return columns, rows


def _build_storage_rows(
    stocks: list[dict[str, Any]],
    shop_names: dict[int, str],
    catalog: Optional[ProductCatalogIndex] = None,
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    columns = [
        ExportColumn("Магазин", True),
        ExportColumn("Название товара", True),
        ExportColumn("ID товара", True),
        ExportColumn("SKU", True),
        ExportColumn("Штрихкод", True),
        ExportColumn("Габаритная группа", True),
        ExportColumn("Оборачиваемость, дней", True),
        ExportColumn("Хранение", True),
        ExportColumn("Всего за хранение последние 30 дней, сум", True),
    ]
    assert {c.name for c in columns} == CANONICAL_STORAGE

    rows: list[dict[str, Any]] = []
    for s in stocks:
        cat = catalog.lookup_stock_row(s) if catalog else None
        barcode = _format_barcode(s.get("barcode")) or (cat.barcode if cat else "")
        product_id = s.get("skuId")
        if cat and cat.product_id is not None:
            product_id = cat.product_id
        stock_qty = s.get("amount")
        if cat and cat.quantity_active is not None:
            stock_qty = cat.quantity_active
        turnover = _compute_turnover_days(
            stock_qty, cat.avg_daily_sales if cat else None
        )
        rows.append(
            {
                "Магазин": _shop_label(shop_names, cat.shop_id) if cat else "",
                "Название товара": s.get("productTitle")
                or s.get("skuTitle")
                or (cat.product_title if cat else ""),
                "ID товара": product_id,
                "SKU": s.get("skuId"),
                "Штрихкод": barcode,
                "Габаритная группа": cat.dimensional_group if cat else "",
                "Оборачиваемость, дней": turnover,
                "Хранение": _pstorage_label(cat.pstorage) if cat else "",
                "Всего за хранение последние 30 дней, сум": cat.paid_storage_amount if cat else "",
            }
        )
    return columns, rows


def _build_inventory_old_rows(
    stocks: list[dict[str, Any]],
    catalog: Optional[ProductCatalogIndex] = None,
    sales_15d_by_sku: Optional[dict[int, float]] = None,
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    columns = [
        ExportColumn("Штрихкод", True),
        ExportColumn("SKU", True),
        ExportColumn("ID товара", True),
        ExportColumn("Наименование", True),
        ExportColumn("В продаже", True),
        ExportColumn("Себест. (сумы)", True),
        ExportColumn("Стоимость продажи (сумы)", True),
        ExportColumn("Оборачиваемость, дней", True),
        ExportColumn("Стоимость хранения 1 дня, сум", True),
        ExportColumn("Среднесуточные продажи", True),
        ExportColumn("Среднесуточные продажи FBO за 15 дней, шт", True),
        ExportColumn("К отправке", True),
        ExportColumn("Общий остаток", True),
    ]
    assert {c.name for c in columns} == CANONICAL_LEFTOUT_OLD

    rows: list[dict[str, Any]] = []
    for s in stocks:
        amount = s.get("amount")
        cat = catalog.lookup_stock_row(s) if catalog else None
        sku_id: Optional[int] = None
        raw_sku = s.get("skuId")
        if raw_sku is not None:
            try:
                sku_id = int(raw_sku)
            except (TypeError, ValueError):
                sku_id = None
        fbo_avg: Any = ""
        if sku_id is not None and sales_15d_by_sku:
            rate = sales_15d_by_sku.get(sku_id)
            if rate is not None:
                fbo_avg = _format_sales_rate(rate)
        turnover = _compute_turnover_days(amount, cat.avg_daily_sales if cat else None)
        rows.append(
            {
                "Штрихкод": _format_barcode(s.get("barcode")) or (cat.barcode if cat else ""),
                "SKU": s.get("skuId"),
                "ID товара": cat.product_id if cat and cat.product_id is not None else s.get("skuId"),
                "Наименование": s.get("productTitle")
                or s.get("skuTitle")
                or (cat.product_title if cat else ""),
                "В продаже": amount,
                "Себест. (сумы)": cat.purchase_price if cat else "",
                "Стоимость продажи (сумы)": cat.sell_price if cat else "",
                "Оборачиваемость, дней": turnover,
                "Стоимость хранения 1 дня, сум": cat.paid_storage_price_item if cat else "",
                "Среднесуточные продажи": cat.avg_daily_sales if cat else "",
                "Среднесуточные продажи FBO за 15 дней, шт": fbo_avg,
                "К отправке": cat.quantity_pending if cat else "",
                "Общий остаток": amount,
            }
        )
    return columns, rows


ReportBuilder = Callable[[UzumApiClient, Optional[int], Optional[int], Optional[list[int]]], tuple[list[ExportColumn], list[dict[str, Any]]]]


def _shops_name_map(client: UzumApiClient) -> dict[int, str]:
    result: dict[int, str] = {}
    for s in client.list_shops():
        raw_id = s.get("id")
        if raw_id is None:
            continue
        try:
            result[int(raw_id)] = str(s.get("name") or "")
        except (TypeError, ValueError):
            continue
    return result


def _build_sales(
    client: UzumApiClient,
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
    shop_ids: Optional[list[int]],
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    shops = _shops_name_map(client)
    resolved_ids = client.resolve_shop_ids(shop_ids)
    items = client.fetch_finance_orders(date_from_ms, date_to_ms, resolved_ids, shops)
    catalog = client.fetch_product_catalog_index(resolved_ids)
    return _build_sales_rows(items, shops, catalog)


def _build_expenses(
    client: UzumApiClient,
    date_from_ms: Optional[int],
    date_to_ms: Optional[int],
    shop_ids: Optional[list[int]],
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    shops = _shops_name_map(client)
    resolved_ids = client.resolve_shop_ids(shop_ids)
    payments = client.fetch_finance_expenses(date_from_ms, date_to_ms, resolved_ids, shops)
    return _build_expenses_rows(payments, shops)


def _build_storage(
    client: UzumApiClient,
    _date_from_ms: Optional[int],
    _date_to_ms: Optional[int],
    shop_ids: Optional[list[int]],
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    shops = _shops_name_map(client)
    resolved_ids = client.resolve_shop_ids(shop_ids)
    catalog = client.fetch_product_catalog_index(resolved_ids)
    stocks = client.fetch_sku_stocks()
    return _build_storage_rows(stocks, shops, catalog)


def _build_inventory_old(
    client: UzumApiClient,
    _date_from_ms: Optional[int],
    _date_to_ms: Optional[int],
    shop_ids: Optional[list[int]],
) -> tuple[list[ExportColumn], list[dict[str, Any]]]:
    shops = _shops_name_map(client)
    resolved_ids = client.resolve_shop_ids(shop_ids)
    catalog = client.fetch_product_catalog_index(resolved_ids)
    sales_15d = client.fetch_avg_daily_sales_15d_by_sku(resolved_ids, catalog, shops)
    stocks = client.fetch_sku_stocks()
    return _build_inventory_old_rows(stocks, catalog, sales_15d)


REPORT_BUILDERS: dict[str, ReportBuilder] = {
    "sales": _build_sales,
    "expenses": _build_expenses,
    "storage": _build_storage,
    "inventory_old": _build_inventory_old,
}


def date_to_epoch_ms(date_str: Optional[str], end_of_day: bool = False) -> Optional[int]:
    """Alias: calendar day boundaries in Uzbekistan (GMT+5)."""
    return calendar_date_to_epoch_ms(date_str, end_of_day=end_of_day)


def build_report(
    report_type: str,
    api_key: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    shop_ids: Optional[list[int]] = None,
) -> tuple[list[ExportColumn], list[dict[str, Any]], str, list[str]]:
    builder = REPORT_BUILDERS.get(report_type)
    if not builder:
        raise ValueError(f"Unknown report type: {report_type}")
    client = UzumApiClient(api_key)
    date_from_ms = date_to_epoch_ms(date_from, end_of_day=False)
    date_to_ms = date_to_epoch_ms(date_to, end_of_day=True)
    columns, rows = builder(client, date_from_ms, date_to_ms, shop_ids)
    return columns, rows, FILE_NAMES.get(report_type, f"{report_type}.xlsx"), list(client.warnings)


def build_xlsx_bytes(
    report_type: str,
    columns: list[ExportColumn],
    rows: list[dict[str, Any]],
) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAMES.get(report_type, "Отчет")[:31]

    bold_font = Font(bold=True)
    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col.name)
        if not col.mapped:
            cell.font = bold_font

    for row_idx, row in enumerate(rows, start=2):
        for col_idx, col in enumerate(columns, start=1):
            value = row.get(col.name, "")
            if value is None:
                value = ""
            ws.cell(row=row_idx, column=col_idx, value=value)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _columns_for_report_type(report_type: str) -> list[ExportColumn]:
    if report_type == "sales":
        unmapped = {"Промокод (сумы)"}
        return [ExportColumn(n, n not in unmapped) for n in sorted(CANONICAL_SALES)]
    if report_type == "expenses":
        return [ExportColumn(n, True) for n in sorted(CANONICAL_EXPENSES)]
    if report_type == "storage":
        return [ExportColumn(n, True) for n in sorted(CANONICAL_STORAGE)]
    if report_type == "inventory_old":
        return [ExportColumn(n, True) for n in sorted(CANONICAL_LEFTOUT_OLD)]
    raise ValueError(f"Unknown report type: {report_type}")


def report_metadata() -> list[dict[str, Any]]:
    """Describe export templates for the UI."""
    hints = {
        "sales": "sells-report",
        "expenses": "expenses-report",
        "storage": "seller-storage-report",
        "inventory_old": "left-out-report",
    }
    meta = []
    tz = timezone_metadata()
    for report_type, sheet in SHEET_NAMES.items():
        cols = _columns_for_report_type(report_type)
        meta.append(
            {
                "id": report_type,
                "sheet_name": sheet,
                "file_name": FILE_NAMES[report_type],
                "hint": hints[report_type],
                "columns": [{"name": c.name, "mapped": c.mapped} for c in cols],
                "needs_date_range": report_type in ("sales", "expenses"),
                **tz,
            }
        )
    return meta
