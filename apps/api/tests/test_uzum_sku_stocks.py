from app.services.uzum_export import _sku_stocks_batch_from_response


def test_sku_stocks_batch_from_response() -> None:
    data = {
        "payload": {
            "skuAmountList": [
                {"skuId": 1, "amount": 5, "barcode": "111"},
                {"skuId": 2, "amount": 0},
            ]
        }
    }
    batch = _sku_stocks_batch_from_response(data)
    assert len(batch) == 2
    assert batch[0]["skuId"] == 1


def test_sku_stocks_batch_empty() -> None:
    assert _sku_stocks_batch_from_response(None) == []
    assert _sku_stocks_batch_from_response({"payload": {}}) == []
