from app.services.uzum_export import (
    _dedupe_finance_payments,
    _payment_operation_id,
)


def test_payment_operation_id_normalizes_float_string() -> None:
    assert _payment_operation_id({"id": 147029297}) == "147029297"
    assert _payment_operation_id({"id": "147029297.0"}) == "147029297"


def test_dedupe_finance_payments_keeps_one_per_id() -> None:
    payments = [
        {"id": 1, "paymentPrice": 100},
        {"id": 1, "paymentPrice": 200},
        {"id": 2, "paymentPrice": 50},
    ]
    out = _dedupe_finance_payments(payments)
    assert len(out) == 2
    assert out[0]["paymentPrice"] == 200
