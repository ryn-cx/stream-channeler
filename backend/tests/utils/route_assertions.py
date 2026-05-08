# TODO: Validate


from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from httpx import Response

from fastapi import status
from fastapi.testclient import TestClient

from tests.users.utils import CreatedUser

type Method = Literal["get", "post", "put", "patch", "delete"]


def make_request(
    client: TestClient,
    method: Method,
    url: str,
    headers: dict[str, str] | None = None,
    parameters: dict[str, Any] | list[Any] | None = None,
) -> Response:
    kwargs: dict[str, Any] = {}
    if headers:
        kwargs["headers"] = headers
    if parameters is not None:
        kwargs["json"] = parameters
    return getattr(client, method)(url, **kwargs)


def assert_not_authenticated(
    client: TestClient,
    method: Method,
    url: str,
    parameters: dict[str, Any] | list[Any] | None = None,
) -> None:
    response = make_request(client, method, url, parameters=parameters)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def assert_not_enough_permission(
    client: TestClient,
    method: Method,
    url: str,
    user: CreatedUser,
    parameters: dict[str, Any] | None = None,
) -> None:
    response = make_request(client, method, url, user.headers, parameters)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def assert_not_found(  # noqa: PLR0913
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: dict[str, Any] | list[Any] | None = None,
) -> None:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == detail


def assert_forbidden(  # noqa: PLR0913
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: dict[str, Any] | list[Any] | None = None,
) -> None:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == detail


def assert_conflict(  # noqa: PLR0913
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: dict[str, Any] | None = None,
) -> None:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == detail


def assert_delete(
    client: TestClient,
    url: str,
    message: str,
    headers: dict[str, str],
) -> None:
    response = make_request(client, "delete", url, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == message


def assert_unprocessable(
    client: TestClient,
    method: Method,
    url: str,
    headers: dict[str, str],
    parameters: dict[str, Any] | list[Any] | None = None,
) -> None:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def assert_success[T: BaseModel](  # noqa: PLR0913
    client: TestClient,
    method: Method,
    url: str,
    output_schema: type[T],
    headers: dict[str, str] | None = None,
    parameters: dict[str, Any] | list[Any] | None = None,
) -> T:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_200_OK
    response_json: dict[str, object] = response.json()
    assert not isinstance(response_json, list)
    return output_schema.model_validate(response_json)


def assert_success_list[T: BaseModel](  # noqa: PLR0913
    client: TestClient,
    method: Method,
    url: str,
    output_schema: type[T],
    headers: dict[str, str] | None = None,
    parameters: dict[str, Any] | list[Any] | None = None,
) -> list[T]:
    response = make_request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_200_OK
    response_json: list[dict[str, object]] = response.json()
    assert isinstance(response_json, list)
    return [output_schema.model_validate(item) for item in response_json]
