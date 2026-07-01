from app.services.uzum_api_helpers import uzum_accept_language
from app.services.uzum_export import UzumApiClient


def test_uzum_accept_language_defaults_to_ru():
    assert uzum_accept_language(None) == "ru"
    assert uzum_accept_language("") == "ru"
    assert uzum_accept_language("ru") == "ru"
    assert uzum_accept_language("ru-RU") == "ru"


def test_uzum_accept_language_uz_variants():
    assert uzum_accept_language("uz") == "uz"
    assert uzum_accept_language("uz-UZ") == "uz"
    assert uzum_accept_language("UZ") == "uz"


def test_uzum_api_client_accept_language_header():
    client = UzumApiClient("key", accept_language="uz")
    assert client._headers["Accept-Language"] == "uz"
