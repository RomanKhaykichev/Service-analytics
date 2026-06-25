"""Tests for bulk-first finance fetch with per-shop fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.uzum_export import (
    ShopUnavailableError,
    UzumApiClient,
    _should_fallback_finance_bulk,
)


@pytest.mark.parametrize(
    "exc,expected",
    [
        (ShopUnavailableError("forbidden"), True),
        (RuntimeError("Uzum API 403: forbidden-001"), True),
        (RuntimeError("Shop is not available"), True),
        (RuntimeError("Uzum API 500: internal"), False),
        (ValueError("bad"), False),
    ],
)
def test_should_fallback_finance_bulk(exc: BaseException, expected: bool) -> None:
    assert _should_fallback_finance_bulk(exc) is expected


def test_fetch_orders_uses_bulk_then_fallback() -> None:
    client = UzumApiClient("key")
    bulk_orders = [{"orderId": 1}]
    per_shop_orders = [[{"orderId": 2}], [{"orderId": 3}]]

    client._fetch_orders_bulk = MagicMock(  # type: ignore[method-assign]
        side_effect=ShopUnavailableError("bulk forbidden")
    )
    client._fetch_orders_for_shop = MagicMock(  # type: ignore[method-assign]
        side_effect=per_shop_orders
    )
    client._collect_per_shop = MagicMock(  # type: ignore[method-assign]
        wraps=client._collect_per_shop
    )

    result = client._fetch_orders_for_shops(
        [10, 20],
        {10: "A", 20: "B"},
        1000,
        2000,
    )

    client._fetch_orders_bulk.assert_called_once()
    client._collect_per_shop.assert_called_once()
    assert result == [{"orderId": 2}, {"orderId": 3}]
    assert any("Сводная выгрузка продаж" in w for w in client.warnings)


def test_fetch_orders_single_shop_skips_bulk() -> None:
    client = UzumApiClient("key")
    client._fetch_orders_bulk = MagicMock()  # type: ignore[method-assign]
    client._fetch_orders_for_shop = MagicMock(return_value=[{"orderId": 1}])  # type: ignore[method-assign]

    result = client._fetch_orders_for_shops([10], {10: "A"}, 1000, 2000)

    client._fetch_orders_bulk.assert_not_called()
    client._fetch_orders_for_shop.assert_called_once_with(10, 1000, 2000, unit_ms=True)
    assert result == [{"orderId": 1}]
