from app.services.uzum_time import expense_cabinet_date_ms, format_datetime, parse_to_epoch_ms


def test_expense_cabinet_date_shifts_05_00_only() -> None:
    # 05:00 UZ (часто хранение / dateCreated) → +1 день
    ms = parse_to_epoch_ms("2026-05-01T00:00:00Z")
    assert ms is not None
    aligned = expense_cabinet_date_ms(ms)
    assert aligned is not None
    assert format_datetime(aligned) == "02.05.2026 05:00"


def test_expense_cabinet_date_keeps_17_00_same_day() -> None:
    # 17:00 UZ (типичная реклама) — без сдвига
    ms = parse_to_epoch_ms("2026-05-01T12:00:00Z")
    assert ms is not None
    aligned = expense_cabinet_date_ms(ms)
    assert aligned is not None
    assert format_datetime(aligned) == "01.05.2026 17:00"
