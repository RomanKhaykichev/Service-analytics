"""Robust parsing for COGS XLSX template import (paste/Excel formats)."""

from app.routes.product_cogs import (
    _is_filled_template_cogs_cell,
    _normalize_barcode_norm,
    _parse_num,
)


def test_normalize_barcode_plain_and_spaces():
    assert _normalize_barcode_norm("1000102783428") == "1000102783428"
    assert _normalize_barcode_norm(" 1000 1027 83428 ") == "1000102783428"
    assert _normalize_barcode_norm("1000102783428.0") == "1000102783428"
    assert _normalize_barcode_norm("1000102783428\u00a0") == "1000102783428"


def test_normalize_barcode_scientific_and_float():
    assert _normalize_barcode_norm("1.000102783428E+12") == "1000102783428"
    assert _normalize_barcode_norm("1,000102783428E+12") == "1000102783428"
    assert _normalize_barcode_norm(1000102783428.0) == "1000102783428"
    assert _normalize_barcode_norm(1000102783428) == "1000102783428"


def test_parse_num_plain_and_decimal():
    assert _parse_num(12500) == 12500.0
    assert _parse_num("12500") == 12500.0
    assert _parse_num("12500.5") == 12500.5
    assert _parse_num("12500,5") == 12500.5
    assert _parse_num("0") == 0.0


def test_parse_num_thousands_currency_nbsp():
    assert _parse_num("12 500") == 12500.0
    assert _parse_num("12\u00a0500") == 12500.0
    assert _parse_num("12\u202f500,50") == 12500.5
    assert _parse_num("12.500,50") == 12500.5
    assert _parse_num("12,500.50") == 12500.5
    assert _parse_num("12500 сум") == 12500.0
    assert _parse_num("12 500 so'm") == 12500.0
    assert _parse_num("₽12 500") == 12500.0
    assert _parse_num("12'500") == 12500.0


def test_filled_cogs_cell_accepts_formatted_text_and_zero_string():
    assert _is_filled_template_cogs_cell("12 500 сум") is True
    assert _is_filled_template_cogs_cell("0") is True
    assert _is_filled_template_cogs_cell("") is False
    assert _is_filled_template_cogs_cell("-") is False
    assert _is_filled_template_cogs_cell(0.0) is False
    assert _is_filled_template_cogs_cell(12500.0) is True
