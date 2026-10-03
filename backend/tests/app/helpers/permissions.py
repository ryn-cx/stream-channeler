# TODO: Validate

from typing import Any, Literal

from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response

from app.config import settings

Method = Literal["get", "post", "patch", "put", "delete"]

UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
FORBIDDEN = status.HTTP_403_FORBIDDEN
NOT_FOUND = status.HTTP_404_NOT_FOUND

REFUSALS = {UNAUTHORIZED, FORBIDDEN}


# TODO: Validate
def url(path: str) -> str:
    """Return the full path of an API route from the part after the version."""
    return f"{settings.API_V1_STR}{path}"


# TODO: Validate
def request(  # noqa: PLR0913 - One argument per part of a request.
    client: TestClient,
    method: Method,
    path: str,
    headers: dict[str, str] | None = None,
    body: Any = None,  # noqa: ANN401 - Whatever the route's body model is.
    params: dict[str, Any] | None = None,
) -> Response:
    """Send one request to an API route."""
    return client.request(
        method.upper(),
        url(path),
        headers=headers or {},
        json=body,
        params=params,
    )


# TODO: Validate
def assert_allowed(  # noqa: PLR0913 - One argument per part of a request.
    client: TestClient,
    method: Method,
    path: str,
    headers: dict[str, str] | None = None,
    body: Any = None,  # noqa: ANN401 - Whatever the route's body model is.
    params: dict[str, Any] | None = None,
) -> Response:
    response = request(client, method, path, headers, body, params)
    assert response.status_code not in REFUSALS, response.text
    return response


# TODO: Validate
def assert_requires_authentication(
    client: TestClient,
    method: Method,
    path: str,
    body: Any = None,  # noqa: ANN401 - Whatever the route's body model is.
    params: dict[str, Any] | None = None,
) -> None:
    """Assert an anonymous request is turned away."""
    response = request(client, method, path, None, body, params)
    assert response.status_code == UNAUTHORIZED, response.text


# TODO: Validate
def assert_forbidden(  # noqa: PLR0913 - One argument per part of a request.
    client: TestClient,
    method: Method,
    path: str,
    headers: dict[str, str],
    body: Any = None,  # noqa: ANN401 - Whatever the route's body model is.
    params: dict[str, Any] | None = None,
) -> None:
    """Assert a signed-in `User` is told the record is not theirs."""
    response = request(client, method, path, headers, body, params)
    assert response.status_code == FORBIDDEN, response.text


# TODO: Validate
def assert_not_found(  # noqa: PLR0913 - One argument per part of a request.
    client: TestClient,
    method: Method,
    path: str,
    headers: dict[str, str],
    body: Any = None,  # noqa: ANN401 - Whatever the route's body model is.
    params: dict[str, Any] | None = None,
) -> None:
    response = request(client, method, path, headers, body, params)
    assert response.status_code == NOT_FOUND, response.text
