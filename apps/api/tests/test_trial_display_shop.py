"""Tests for trial display shop resolution."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.utils.trial_shop import get_effective_trial_display_shop, set_trial_permitted_shop


def test_effective_trial_display_reads_allowed_shops(monkeypatch):
    db = MagicMock()
    user_id = uuid4()

    monkeypatch.setattr(
        "app.utils.trial_shop.is_trial_plan_user",
        lambda _db, _uid: True,
    )
    monkeypatch.setattr(
        "app.utils.trial_shop.get_user_allowed_shops_list",
        lambda _db, _uid: ["Admin Shop"],
    )

    assert get_effective_trial_display_shop(db, user_id) == "Admin Shop"


def test_effective_trial_display_empty_without_allowed(monkeypatch):
    db = MagicMock()
    user_id = uuid4()

    monkeypatch.setattr(
        "app.utils.trial_shop.is_trial_plan_user",
        lambda _db, _uid: True,
    )
    monkeypatch.setattr(
        "app.utils.trial_shop.get_user_allowed_shops_list",
        lambda _db, _uid: None,
    )

    assert get_effective_trial_display_shop(db, user_id) is None


def test_set_trial_permitted_shop_writes_allowed_list(monkeypatch):
    db = MagicMock()
    user_id = uuid4()
    allowed: list[str] = []

    monkeypatch.setattr(
        "app.utils.trial_shop.is_trial_plan_user",
        lambda _db, _uid: True,
    )
    monkeypatch.setattr(
        "app.utils.trial_shop.get_effective_trial_display_shop",
        lambda _db, _uid: None,
    )
    monkeypatch.setattr(
        "app.utils.trial_shop._canonicalize_loaded_shop_label",
        lambda _db, _uid, shop: shop,
    )
    monkeypatch.setattr(
        "app.utils.trial_shop.set_user_allowed_shops_list",
        lambda _db, _uid, shops: allowed.extend(shops),
    )

    result = set_trial_permitted_shop(db, user_id, "My Shop", allow_overwrite=True)
    assert result == "My Shop"
    assert allowed == ["My Shop"]
