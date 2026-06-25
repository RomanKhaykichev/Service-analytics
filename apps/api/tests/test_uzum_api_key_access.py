"""Tests for limited Uzum API key access validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.uzum_api_helpers import (
    UZUM_KEY_INSUFFICIENT_ACCESS,
    build_query_params,
    extract_shop_ids_from_shops_response,
    validate_api_key_access,
)


def test_build_query_params_repeats_shop_ids():
    pairs = build_query_params(
        {"page": 0, "size": 1, "shopIds": [10, 20]},
    )
    assert ("page", 0) in pairs
    assert ("size", 1) in pairs
    shop_values = [v for k, v in pairs if k == "shopIds"]
    assert shop_values == [10, 20]


def test_extract_shop_ids_from_shops_response():
    body = [{"id": 76152, "name": "Shop A"}, {"id": "99", "name": "B"}]
    assert extract_shop_ids_from_shops_response(body) == [76152, 99]


def _mock_response(status: int, body, headers=None):
    resp = MagicMock()
    resp.status_code = status
    hdrs = dict(headers or {})
    if isinstance(body, (dict, list)) and "content-type" not in {k.lower() for k in hdrs}:
        hdrs["content-type"] = "application/json"
    resp.headers = hdrs
    if isinstance(body, (dict, list)):
        resp.json.return_value = body
        resp.text = str(body)
    else:
        resp.json.side_effect = ValueError()
        resp.text = body
    return resp


@patch("app.services.uzum_api_helpers.requests.get")
def test_validate_api_key_access_ok(mock_get):
    mock_get.side_effect = [
        _mock_response(200, [{"id": 100, "name": "A"}]),
        _mock_response(200, {"productList": []}),
        _mock_response(200, {"orderItems": []}),
        _mock_response(200, {"payload": {"payments": []}}),
    ]
    result = validate_api_key_access("test-key")
    assert result.ok is True
    assert result.shop_ids == [100]


@patch("app.services.uzum_api_helpers.requests.get")
def test_validate_api_key_access_ok_when_product_forbidden(mock_get):
    mock_get.side_effect = [
        _mock_response(200, [{"id": 100, "name": "A"}]),
        _mock_response(
            403,
            {"errors": [{"code": "forbidden-001", "message": "Shop is not available"}]},
        ),
        _mock_response(200, {"orderItems": []}),
        _mock_response(200, {"payload": {"payments": []}}),
    ]
    result = validate_api_key_access("test-key")
    assert result.ok is True
    assert result.probes[0].product_ok is False
    assert result.probes[0].orders_ok is True
    assert result.probes[0].expenses_ok is True


@patch("app.services.uzum_api_helpers.requests.get")
def test_validate_api_key_access_ok_orders_only(mock_get):
    """Connect succeeds when orders work even if expenses are forbidden."""
    mock_get.side_effect = [
        _mock_response(200, [{"id": 100, "name": "A"}]),
        _mock_response(200, {"productList": []}),
        _mock_response(200, {"orderItems": []}),
        _mock_response(
            403,
            {"errors": [{"code": "forbidden-001", "message": "Shop is not available"}]},
        ),
    ]
    result = validate_api_key_access("test-key")
    assert result.ok is True
    assert result.probes[0].orders_ok is True
    assert result.probes[0].expenses_ok is False


@patch("app.services.uzum_api_helpers.requests.get")
def test_validate_api_key_access_insufficient_finance(mock_get):
    mock_get.side_effect = [
        _mock_response(200, [{"id": 100, "name": "A"}]),
        _mock_response(200, {"productList": []}),
        _mock_response(
            403,
            {"errors": [{"code": "forbidden-001", "message": "Shop is not available"}]},
        ),
        _mock_response(200, {"payload": {"payments": []}}),
    ]
    result = validate_api_key_access("test-key")
    assert result.ok is False
    assert result.error == UZUM_KEY_INSUFFICIENT_ACCESS
    assert result.shop_ids == [100]
    assert result.probes[0].orders_ok is False


@patch("app.services.uzum_api_helpers.requests.get")
def test_validate_api_key_access_no_shops(mock_get):
    mock_get.return_value = _mock_response(200, [])
    result = validate_api_key_access("test-key")
    assert result.ok is False
    assert result.shop_ids == []
