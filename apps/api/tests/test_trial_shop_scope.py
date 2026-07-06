"""Tests for trial shop selection helpers."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.services.uzum_shop_scope import candidate_shop_ids_for_user


def test_candidate_shop_ids_trial_loads_all_shops(monkeypatch):
    db = MagicMock()
    user_id = uuid4()
    name_map = {10: "A", 20: "B", 30: "C"}

    monkeypatch.setattr(
        "app.services.uzum_shop_scope.get_user_allowed_shops_list",
        lambda _db, _uid: None,
    )
    monkeypatch.setattr(
        "app.services.uzum_shop_scope.is_trial_plan_user",
        lambda _db, _uid: True,
    )

    assert candidate_shop_ids_for_user(db, user_id, name_map) == [10, 20, 30]
