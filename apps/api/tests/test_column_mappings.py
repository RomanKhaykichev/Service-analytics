# -*- coding: utf-8 -*-
"""
Unit tests for column header mapping (UZ -> canonical RU).
"""
import pytest
from app.utils.column_mappings import (
    normalize_header,
    normalize_header_lower,
    map_headers_to_canonical,
    detect_language,
    MissingRequiredColumnsError,
    CANONICAL_BY_FILE_TYPE,
    UZ_TO_RU_BY_FILE_TYPE,
)


def test_normalize_header():
    assert normalize_header("  Штрихкод  ") == "Штрихкод"
    assert normalize_header("Shtrix kod") == "Shtrix kod"
    assert normalize_header("  a   b  ") == "a b"


def test_normalize_header_lower():
    assert normalize_header_lower("  Shtrix kod  ") == "shtrix kod"


def test_sales_ru_passthrough():
    """RU headers pass through unchanged."""
    headers = ["Статус", "Дата создания", "№ заказа", "Штрихкод"]
    required = ["Дата создания", "№ заказа", "Штрихкод"]
    rename, lang = map_headers_to_canonical("sales", headers, required)
    assert lang == "ru"
    assert rename == {h: h for h in headers}


def test_sales_uz_mapped():
    """UZ headers (from mapping) map to canonical RU."""
    # Use keys from UZ_TO_RU_SALES (normalized lower)
    uz_headers = ["Holat", "Yaratilgan sana", "Buyurtma raqami", "Shtrix kod", "SKU", "Mahsulot nomi"]
    required = ["Дата создания", "№ заказа", "Штрихкод"]
    rename, lang = map_headers_to_canonical("sales", uz_headers, required)
    assert lang == "uz"
    assert rename.get("Yaratilgan sana") == "Дата создания"
    assert rename.get("Buyurtma raqami") == "№ заказа"
    assert rename.get("Shtrix kod") == "Штрихкод"


def test_expenses_ru_required():
    """Expenses: required columns present (RU)."""
    headers = ["ID операции", "Дата списания", "Источник", "Услуга"]
    required = ["ID операции", "Дата списания"]
    rename, _ = map_headers_to_canonical("expenses", headers, required)
    assert "ID операции" in rename.values()
    assert "Дата списания" in rename.values()


def test_leftout_old_required():
    """Leftout_old: required canonical columns."""
    headers = ["Штрихкод", "В продаже", "Себест. (сумы)", "Стоимость продажи (сумы)"]
    required = ["Штрихкод", "В продаже", "Себест. (сумы)", "Стоимость продажи (сумы)"]
    rename, _ = map_headers_to_canonical("leftout_old", headers, required)
    assert set(rename.values()) == set(required)


def test_missing_required_raises():
    """Missing required canonical columns raises MissingRequiredColumnsError."""
    headers = ["Статус"]  # missing required for sales
    required = ["Дата создания", "№ заказа", "Штрихкод"]
    with pytest.raises(MissingRequiredColumnsError) as exc_info:
        map_headers_to_canonical("sales", headers, required)
    assert "Дата создания" in str(exc_info.value) or "Не найдены" in str(exc_info.value)


def test_duplicate_canonical_takes_first():
    """When two headers map to same canonical, only the first is used (no error)."""
    headers = ["Штрихкод", "Shtrix kod"]  # both -> Штрихкод
    required = ["Штрихкод"]
    rename, _ = map_headers_to_canonical("sales", headers, required)
    # First header wins; second is not renamed to avoid duplicate column
    assert rename.get("Штрихкод") == "Штрихкод"
    assert "Shtrix kod" not in rename or rename.get("Shtrix kod") != "Штрихкод"
    assert "Штрихкод" in set(rename.values())


def test_detect_language_ru():
    headers_ru = ["Статус", "Дата создания", "Штрихкод"]
    assert detect_language("sales", headers_ru) == "ru"


def test_detect_language_uz():
    headers_uz = ["Holat", "Yaratilgan sana", "Shtrix kod"]
    assert detect_language("sales", headers_uz) == "uz"


def test_storage_canonical_set():
    """Storage file type has expected canonical columns."""
    assert "Магазин" in CANONICAL_BY_FILE_TYPE["storage"]
    assert "Штрихкод" in CANONICAL_BY_FILE_TYPE["storage"]


def test_uz_mapping_has_required_for_sales():
    """UZ mapping for sales includes required columns."""
    required = ["Дата создания", "№ заказа", "Штрихкод"]
    uz_map = UZ_TO_RU_BY_FILE_TYPE["sales"]
    mapped_ru = set(uz_map.values())
    for r in required:
        assert r in mapped_ru, f"Required '{r}' should have UZ mapping"


def test_sales_uz_um_export_headers():
    """Headers from real UZUM UZ export (Yaratilish sanasi, Tushim (soʻm), etc.) map to canonical."""
    headers = [
        "Holati", "Yaratilish sanasi", "Olinish sanasi", "Buyurtma raqami", "Shtrixkod", "SKU",
        "Nomi", "Turkumi", "Soni", "Qaytarishlar", "Tushim (soʻm)",
        "Komissiya va logistika chiqarib tashlangan tushim (soʻm)",
        "Marketpleys komissiyasi (soʻm)", "Narxi (soʻm)", "Promokod (soʻm)", "Tannarxi (soʻm)",
        "Logistika to'lovi",
    ]
    required = ["Дата создания", "№ заказа", "Штрихкод"]
    rename, lang = map_headers_to_canonical("sales", headers, required)
    assert lang == "uz"
    assert rename["Yaratilish sanasi"] == "Дата создания"
    assert rename["Buyurtma raqami"] == "№ заказа"
    assert rename["Shtrixkod"] == "Штрихкод"
