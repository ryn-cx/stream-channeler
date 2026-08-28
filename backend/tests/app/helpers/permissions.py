# TODO: Validate
"""Helpers for the API tests.

An API test asks one question: does this route let the right people through and
turn the wrong ones away. What the route then does with the request is the
service's own, and is tested against the service directly.
"""

from typing import Any, Literal

from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response

from app.config import settings

Method = Literal["get", "post", "patch", "put", "delete"]

UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
FORBIDDEN = status.HTTP_403_FORBIDDEN
NOT_FOUND = status.HTTP_404_NOT_FOUND

# What a route answers when it turns a request away. A route that lets the
# request through can answer anything else, including a validation error over a
# body the API test did not bother to fill in.
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
    """Assert the route let the request through, whatever it then answered."""
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
    """Assert the route answers that the record an id names does not exist."""
    response = request(client, method, path, headers, body, params)
    assert response.status_code == NOT_FOUND, response.text
