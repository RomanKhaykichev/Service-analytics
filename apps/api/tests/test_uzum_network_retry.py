from http.client import IncompleteRead

import pytest
from requests.exceptions import ConnectionError, ReadTimeout

from app.services.uzum_export import _is_transient_request_error


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionError("reset"),
        ReadTimeout("timed out"),
        IncompleteRead(b"partial", 100),
        RuntimeError("Connection broken: IncompleteRead(6137 bytes read, 4103 more expected)"),
    ],
)
def test_transient_request_errors(exc: BaseException) -> None:
    assert _is_transient_request_error(exc) is True


def test_non_transient_request_error() -> None:
    assert _is_transient_request_error(ValueError("bad")) is False
