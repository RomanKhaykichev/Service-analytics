# -*- coding: utf-8 -*-
"""
Маппинг значений ячеек UZ -> RU для корректного расчёта метрик.
После загрузки заголовки уже канонические (RU); значения в ячейках могут быть на узбекском.
Нормализация: trim, lower, замена ʻ и ' для сопоставления.
"""
from typing import Dict
import pandas as pd


def _norm_val(v: str) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip().lower()
    s = s.replace("\u02bb", "'").replace("\u2019", "'").replace("\u2018", "'")
    return " ".join(s.split())


# Статус заказа (sales): UZ (normalized lower) -> RU (lower, как в fact_sales и get_status_conditions)
STATUS_UZ_TO_RU: Dict[str, str] = {
    _norm_val("Yetkazilgan"): "завершен",
    _norm_val("Yakunlangan"): "завершен",
    _norm_val("Yakunlandi"): "завершен",  # в выгрузке UZUM именно так
    _norm_val("Tugatilgan"): "завершен",
    _norm_val("Qayta ishlashda"): "в обработке",
    _norm_val("Qayta ishlanmoqda"): "в обработке",  # UZUM export
    _norm_val("Jarayonda"): "в обработке",
    _norm_val("Bekor qilindi"): "отменен",
    _norm_val("Rad etildi"): "отменен",
}
# Дополнительно: подстроки для нечётких совпадений (если полное значение не найдено)
STATUS_UZ_PATTERNS_TO_RU = [
    ("yetkazilgan", "завершен"),
    ("yakunlangan", "завершен"),
    ("yakunlandi", "завершен"),
    ("qayta ishlashda", "в обработке"),
    ("qayta ishlanmoqda", "в обработке"),
    ("jarayonda", "в обработке"),
    ("bekor qilindi", "отменен"),
    ("rad etildi", "отменен"),
]


def _map_status(val: str) -> str:
    n = _norm_val(val)
    if not n:
        return val
    if n in STATUS_UZ_TO_RU:
        return STATUS_UZ_TO_RU[n]
    for uz_sub, ru in STATUS_UZ_PATTERNS_TO_RU:
        if uz_sub in n:
            return ru
    return val


# Источник (expenses): UZ -> RU (для сравнения upper(trim(source)) = 'СКЛАД' | 'МАРКЕТИНГ')
SOURCE_UZ_TO_RU: Dict[str, str] = {
    _norm_val("Sklad"): "Склад",
    _norm_val("Ombor"): "Склад",
    _norm_val("Marketing"): "Маркетинг",
    _norm_val("Reklama"): "Маркетинг",
}


def _map_source(val: str) -> str:
    n = _norm_val(val)
    if not n:
        return val
    return SOURCE_UZ_TO_RU.get(n, val)


# Тип операции (expenses): UZ -> RU (Оплата, Возврат)
OPERATION_TYPE_UZ_TO_RU: Dict[str, str] = {
    _norm_val("To'lov"): "Оплата",
    _norm_val("Tolov"): "Оплата",
    _norm_val("To‘lov"): "Оплата",
    _norm_val("Qaytarish"): "Возврат",
}


def _map_operation_type(val: str) -> str:
    n = _norm_val(val)
    if not n:
        return val
    return OPERATION_TYPE_UZ_TO_RU.get(n, val)


# Услуга (expenses): для штрафов LIKE '%Штраф%' — UZ "Jarima" (или подстрока) -> добавить/заменить на "Штраф"
SERVICE_UZ_TO_RU: Dict[str, str] = {
    _norm_val("Jarima"): "Штраф",
    _norm_val("Saqlash"): "Хранение",
    _norm_val("Reklama"): "Реклама",
}


def _map_service(val: str) -> str:
    n = _norm_val(val)
    if not n:
        return val
    if n in SERVICE_UZ_TO_RU:
        return SERVICE_UZ_TO_RU[n]
    # Подстрока: если в описании есть "jarima" (штраф), добавляем "Штраф" для условия LIKE '%Штраф%'
    if "jarima" in n:
        return (val.strip() + " Штраф") if val.strip() else "Штраф"
    return val


# Габаритная группа (storage/seller): UZ -> RU (СГТ, МГТ, БГТ) — соответствие выгрузок RU/Узб, единый цвет в UI
# RU в выгрузках: СГТ, МГТ, БГТ. Узб: Kichik/O'rta/Katta и варианты (gabaritli, o'lchamli — из выгрузок Uzum)
SIZE_GROUP_UZ_TO_RU: Dict[str, str] = {
    _norm_val("Kichik"): "СГТ",
    _norm_val("Kichik gabaritli"): "СГТ",
    _norm_val("Kichik o'lchamli"): "СГТ",
    _norm_val("Kichik olchamli"): "СГТ",
    _norm_val("O'rta"): "МГТ",
    _norm_val("Orta"): "МГТ",
    _norm_val("O'rta gabaritli"): "МГТ",
    _norm_val("O'rta o'lchamli"): "МГТ",
    _norm_val("Orta o'lchamli"): "МГТ",
    _norm_val("Katta"): "БГТ",
    _norm_val("Katta gabaritli"): "БГТ",
    _norm_val("Katta o'lchamli"): "БГТ",
    _norm_val("Katta olchamli"): "БГТ",
}


def _map_size_group(val: str) -> str:
    n = _norm_val(val)
    if not n:
        return val
    if n in SIZE_GROUP_UZ_TO_RU:
        return SIZE_GROUP_UZ_TO_RU[n]
    # подстрока: kichik -> СГТ, o'rta/orta -> МГТ, katta -> БГТ (все варианты из выгрузок)
    if "kichik" in n:
        return "СГТ"
    if "o'rta" in n or "orta" in n:
        return "МГТ"
    if "katta" in n:
        return "БГТ"
    return val


def apply_value_mappings(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
    """
    Заменить значения ячеек UZ на RU в колонках, по которым считаются метрики.
    Вызывать после маппинга заголовков (canonical columns).
    """
    if df.empty:
        return df
    if file_type == "sales":
        if "Статус" in df.columns:
            df = df.copy()
            df["Статус"] = df["Статус"].astype(str).apply(lambda x: _map_status(x))
    elif file_type == "expenses":
        df = df.copy()
        if "Источник" in df.columns:
            df["Источник"] = df["Источник"].astype(str).apply(lambda x: _map_source(x))
        if "Услуга" in df.columns:
            df["Услуга"] = df["Услуга"].astype(str).apply(lambda x: _map_service(x))
        if "Тип операции" in df.columns:
            df["Тип операции"] = df["Тип операции"].astype(str).apply(lambda x: _map_operation_type(x))
    # Габаритная группа: не переводим значения при импорте — отображение берётся из файла (KGT/MGT/BGT в UZ, СГТ/МГТ/БГТ в RU), цвет задаётся на фронте по соответствию.
    return df
