"""Tests for Uzum sync shop scope resolution."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.uzum_api_helpers import ShopAccessProbe
from app.services.uzum_shop_scope import (
    candidate_shop_ids_for_user,
    resolve_accessible_shop_ids,
    shops_id_name_map,
)


def test_shops_id_name_map_from_list_shops():
    client = MagicMock()
    client.list_shops.return_value = [
        {"id": 10, "name": "Shop A"},
        {"id": "20", "name": "Shop B"},
    ]
    assert shops_id_name_map(client) == {10: "Shop A", 20: "Shop B"}


def test_resolve_accessible_reuses_prior_probes():
    client = MagicMock()
    client._filter_available_shops.return_value = [20]
    name_map = {10: "A", 20: "B", 30: "C"}
    probes = [
        ShopAccessProbe(shop_id=10, orders_ok=True),
        ShopAccessProbe(shop_id=30, orders_ok=False),
    ]
    result = resolve_accessible_shop_ids(
        client,
        [10, 20, 30],
        name_map,
        prior_probes=probes,
    )
    assert result == [10, 20]
    client._filter_available_shops.assert_called_once()
    probed_ids = client._filter_available_shops.call_args[0][0]
    assert probed_ids == [20]


def test_resolve_accessible_preserves_candidate_order():
    client = MagicMock()
    client._filter_available_shops.return_value = [30, 10]
    name_map = {10: "A", 20: "B", 30: "C"}
    result = resolve_accessible_shop_ids(client, [30, 10, 20], name_map)
    assert result == [30, 10]


def test_candidate_shop_ids_explicit_allowlist(monkeypatch):
    db = MagicMock()
    user_id = uuid4()
    name_map = {10: "Alpha", 20: "Beta"}

    monkeypatch.setattr(
        "app.services.uzum_shop_scope.get_user_allowed_shops_list",
        lambda _db, _uid: ["Beta"],
    )

    assert candidate_shop_ids_for_user(db, user_id, name_map) == [20]


def test_candidate_shop_ids_all_when_no_override(monkeypatch):
    db = MagicMock()
    user_id = uuid4()
    name_map = {10: "A", 20: "B"}

    monkeypatch.setattr(
        "app.services.uzum_shop_scope.get_user_allowed_shops_list",
        lambda _db, _uid: None,
    )
    monkeypatch.setattr(
        "app.services.uzum_shop_scope.get_user_max_shops",
        lambda _db, _uid: None,
    )

    assert candidate_shop_ids_for_user(db, user_id, name_map) == [10, 20]
