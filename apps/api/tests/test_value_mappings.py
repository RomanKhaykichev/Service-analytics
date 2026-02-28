# -*- coding: utf-8 -*-
"""
Unit tests for cell value mapping UZ -> RU (status, source, service, operation_type).
"""
import pandas as pd
from app.utils.value_mappings import apply_value_mappings


def test_apply_value_mappings_sales():
    df = pd.DataFrame({"Статус": ["Yetkazilgan", "Qayta ishlanmoqda", "Bekor qilindi"]})
    out = apply_value_mappings(df, "sales")
    assert list(out["Статус"]) == ["завершен", "в обработке", "отменен"]


def test_apply_value_mappings_expenses():
    df = pd.DataFrame({
        "Источник": ["Ombor", "Marketing"],
        "Услуга": ["Saqlash", "Jarima"],
        "Тип операции": ["To'lov", "Qaytarish"],
    })
    out = apply_value_mappings(df, "expenses")
    assert list(out["Источник"]) == ["Склад", "Маркетинг"]
    assert list(out["Услуга"]) == ["Хранение", "Штраф"]
    assert list(out["Тип операции"]) == ["Оплата", "Возврат"]


def test_apply_value_mappings_storage_size_group_unchanged():
    """Габаритная группа не переводится при импорте — отображение из файла (KGT/MGT/BGT в UZ), цвет на фронте."""
    df = pd.DataFrame({"Габаритная группа": ["KGT", "MGT", "BGT", "СГТ", "МГТ"]})
    out = apply_value_mappings(df, "storage")
    assert list(out["Габаритная группа"]) == ["KGT", "MGT", "BGT", "СГТ", "МГТ"]


def test_apply_value_mappings_other_file_type_unchanged():
    df = pd.DataFrame({"A": [1, 2]})
    out = apply_value_mappings(df, "storage")
    pd.testing.assert_frame_equal(out, df)
