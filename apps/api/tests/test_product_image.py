from app.routes.charts import _extract_product_image_url_from_data
from app.services.uzum_export import _extract_preview_image_url
from app.utils.product_image import (
    is_allowed_product_image_host,
    normalize_product_image_url,
    resolve_product_image_url,
    uzum_cdn_fetch_candidates,
)


def test_extract_preview_image_prefers_sku_then_product():
    sku = {"previewImage": ""}
    product = {"previewImg": "https://images.uzum.uz/a/b.jpg"}
    assert _extract_preview_image_url(sku, product) == "https://images.uzum.uz/a/b.jpg"


def test_extract_preview_image_from_photo_object():
    sku = {"photo": {"high": "https://images.uzum.uz/hi.jpg", "low": "https://images.uzum.uz/lo.jpg"}}
    product = {}
    assert _extract_preview_image_url(sku, product) == "https://images.uzum.uz/hi.jpg"


def test_normalize_relative_and_protocol_relative():
    assert normalize_product_image_url("//images.uzum.uz/x.jpg") == "https://images.uzum.uz/x.jpg"
    assert normalize_product_image_url("/x/y.jpg") == "https://images.uzum.uz/x/y.jpg"


def test_normalize_bare_hash():
    assert normalize_product_image_url("d4binkej76onqt5j4ijg") == (
        "https://images.uzum.uz/d4binkej76onqt5j4ijg"
    )


def test_normalize_http_to_https():
    assert normalize_product_image_url("http://images.uzum.uz/x.jpg") == (
        "https://images.uzum.uz/x.jpg"
    )


def test_normalize_rejects_seller_links():
    assert normalize_product_image_url("https://seller.uzum.uz/product/123") is None


def test_uzum_cdn_bare_hash_gets_thumbnail_suffix():
    url = "https://images.uzum.uz/d4binkej76onqt5j4ijg"
    assert uzum_cdn_fetch_candidates(url) == [
        "https://images.uzum.uz/d4binkej76onqt5j4ijg/t_product_240_high.jpg",
        "https://images.uzum.uz/d4binkej76onqt5j4ijg/original.jpg",
        "https://images.uzum.uz/d4binkej76onqt5j4ijg/t_product_540_high.jpg",
    ]


def test_extract_from_leftout_data_json():
    data = {"Наименование": "Test", "Ссылка на товар": "https://images.uzum.uz/item/1.webp"}
    assert _extract_product_image_url_from_data(data) == "https://images.uzum.uz/item/1.webp"


def test_extract_from_bare_uzum_cdn_hash():
    data = {"Ссылка на товар": "https://images.uzum.uz/d4binkej76onqt5j4ijg"}
    assert _extract_product_image_url_from_data(data) == (
        "https://images.uzum.uz/d4binkej76onqt5j4ijg/t_product_240_high.jpg"
    )


def test_resolve_bare_hash_string():
    assert resolve_product_image_url("d4binkej76onqt5j4ijg") == (
        "https://images.uzum.uz/d4binkej76onqt5j4ijg/t_product_240_high.jpg"
    )


def test_allowed_image_hosts():
    assert is_allowed_product_image_host("images.uzum.uz")
    assert not is_allowed_product_image_host("evil.example.com")
