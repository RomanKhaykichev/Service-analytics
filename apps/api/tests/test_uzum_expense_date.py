from app.services.uzum_time import expense_cabinet_date_ms, format_datetime, parse_to_epoch_ms


def test_expense_cabinet_date_adds_one_uz_day() -> None:
    # Open API dateService: 2026-05-01 12:00 UTC = 01.05.2026 17:00 in Tashkent
    ms = parse_to_epoch_ms("2026-05-01T12:00:00Z")
    assert ms is not None
    aligned = expense_cabinet_date_ms(ms)
    assert aligned is not None
    assert format_datetime(aligned) == "02.05.2026 17:00"
