"""Resolve Uzum shop scope for sync: candidates → accessible shop_ids."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.routes.imports import get_user_max_shops
from app.services.uzum_api_helpers import ShopAccessProbe
from app.services.uzum_export import UzumApiClient
from app.utils.tenant_shop_allowlist import (
    get_user_allowed_shops_list,
    norm_shop_label,
    resolve_allowed_shop_labels,
)
from app.utils.trial_shop import is_trial_plan_user

logger = logging.getLogger(__name__)


def shops_id_name_map(client: UzumApiClient) -> dict[int, str]:
    result: dict[int, str] = {}
    for shop in client.list_shops():
        if not isinstance(shop, dict):
            continue
        raw_id = shop.get("id")
        if raw_id is None:
            continue
        try:
            shop_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        result[shop_id] = str(shop.get("name") or "").strip() or f"ID {shop_id}"
    return result


def candidate_shop_ids_for_user(
    db: Session,
    user_id: UUID,
    name_map: dict[int, str],
) -> list[int]:
    """Narrow /v1/shops ids using admin allowlist or tariff before finance probe."""
    if not name_map:
        return []

    norm_to_id = {norm_shop_label(name): sid for sid, name in name_map.items()}
    explicit = get_user_allowed_shops_list(db, user_id)
    # На trial allowed_shops задаёт только разрешённый магазин в UI, не сужает выгрузку.
    if explicit and not is_trial_plan_user(db, user_id):
        candidates: list[int] = []
        for label in explicit:
            sid = norm_to_id.get(norm_shop_label(label))
            if sid is not None and sid not in candidates:
                candidates.append(sid)
        return candidates

    if is_trial_plan_user(db, user_id):
        return list(name_map.keys())

    max_shops = get_user_max_shops(db, user_id)
    if max_shops is not None:
        allowed_labels, _ = resolve_allowed_shop_labels(
            db,
            user_id,
            list(name_map.values()),
            max_shops=max_shops,
        )
        candidates = []
        for label in allowed_labels:
            sid = norm_to_id.get(norm_shop_label(label))
            if sid is not None and sid not in candidates:
                candidates.append(sid)
        if candidates:
            return candidates

    return list(name_map.keys())


def resolve_accessible_shop_ids(
    client: UzumApiClient,
    candidate_ids: list[int],
    name_map: dict[int, str],
    prior_probes: Optional[list[ShopAccessProbe]] = None,
) -> list[int]:
    """
    Finance orders probe for shops not covered by prior validate_api_key_access probes.
    Preserves candidate order.
    """
    if not candidate_ids:
        return []

    orders_known: dict[int, bool] = {}
    if prior_probes:
        for probe in prior_probes:
            if probe.shop_id in candidate_ids:
                orders_known[probe.shop_id] = probe.orders_ok

    accessible_set: set[int] = {
        sid for sid in candidate_ids if orders_known.get(sid) is True
    }
    to_probe = [sid for sid in candidate_ids if sid not in orders_known]
    if to_probe:
        probed = client._filter_available_shops(
            to_probe,
            name_map,
            client._probe_shop_for_orders,
            pause_between=False,
        )
        accessible_set.update(probed)

    return [sid for sid in candidate_ids if sid in accessible_set]


def prepare_sync_shop_scope(
    client: UzumApiClient,
    db: Session,
    user_id: UUID,
    prior_probes: Optional[list[ShopAccessProbe]] = None,
) -> tuple[list[int], dict[int, str]]:
    """
    Single entry: /v1/shops (cached on client) → candidates → accessible ids.
    Raises RuntimeError when no shop is reachable for finance/orders.
    """
    name_map = shops_id_name_map(client)
    if not name_map:
        raise RuntimeError(
            "Не найдены магазины в Uzum API (/v1/shops). Проверьте API-ключ и права доступа."
        )

    candidates = candidate_shop_ids_for_user(db, user_id, name_map)
    if not candidates:
        explicit = get_user_allowed_shops_list(db, user_id)
        if explicit:
            raise RuntimeError(
                "Магазины из списка allowed_shops не найдены в Uzum API (/v1/shops). "
                "Проверьте названия в админке."
            )
        raise RuntimeError(
            "Не удалось определить магазины для выгрузки. Проверьте тариф и /v1/shops."
        )

    accessible = resolve_accessible_shop_ids(
        client, candidates, name_map, prior_probes=prior_probes
    )
    if not accessible:
        raise RuntimeError(
            "Нет магазинов с доступом к финансовым продажам (finance/orders) для текущего API-ключа."
        )

    logger.info(
        "Uzum sync shop scope user=%s candidates=%s accessible=%s",
        user_id,
        candidates,
        accessible,
    )
    return accessible, name_map
