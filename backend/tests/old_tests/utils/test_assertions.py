# TODO: Validate
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from tests.users.utils import CreatedUser

type Method = Literal["get", "post", "put", "patch", "delete"]


def _request(
    client: TestClient,
    method: Method,
    url: str,
    headers: dict[str, str] | None = None,
    parameters: Any = None,
) -> Any:
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
    parameters: Any = None,
) -> None:
    response = _request(client, method, url, parameters=parameters)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def assert_not_enough_permission(
    client: TestClient,
    method: Method,
    url: str,
    user: CreatedUser,
    parameters: Any = None,
) -> None:
    response = _request(
        client,
        method,
        url,
        headers=user.headers,
        parameters=parameters,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def assert_not_found(
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: Any = None,
) -> None:
    response = _request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == detail


def assert_forbidden(
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: Any = None,
) -> None:
    response = _request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == detail


def _normalize_value(value: Any) -> Any:
    """Normalize values for comparison (e.g. timezone-aware datetime strings)."""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return value


def assert_input_matches_output(
    input_data: dict[str, Any],
    output: Any,
) -> None:
    """Assert that every input field present in the output has the same value."""
    output_data = output.model_dump(mode="json")
    for key, input_value in input_data.items():
        if key not in output_data:
            continue
        assert _normalize_value(output_data[key]) == _normalize_value(input_value), (
            f"Field '{key}': expected {input_value!r}, got {output_data[key]!r}"
        )


def assert_success[T: SQLModel](
    client: TestClient,
    method: Method,
    url: str,
    output_model: type[T],
    headers: dict[str, str],
    parameters: dict[str, Any] | None = None,
) -> T:
    response = _request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_200_OK
    content = output_model.model_validate(response.json())
    assert_input_matches_output(parameters, content)
    return content


def assert_saved_to_db(
    db: Session,
    model: type[Any],
    record_id: uuid.UUID,
    input_data: dict[str, Any],
    *,
    updated: bool = False,
) -> None:
    db.commit()
    record = db.exec(select(model).where(model.id == record_id)).one()
    if updated:
        record_data = record.model_dump(mode="json")
        if "modified_at" in input_data:
            original_modified = _normalize_value(input_data["modified_at"])
            current_modified = _normalize_value(record_data["modified_at"])
            assert current_modified >= original_modified, (
                f"modified_at should have incremented: {original_modified!r} -> {current_modified!r}"
            )
        filtered_data = {k: v for k, v in input_data.items() if k != "modified_at"}
        assert_input_matches_output(filtered_data, record)
    else:
        assert_input_matches_output(input_data, record)


def assert_delete(
    client: TestClient,
    url: str,
    message: str,
    headers: dict[str, str],
) -> None:
    response = _request(client, "delete", url, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == message


def assert_conflict(
    client: TestClient,
    method: Method,
    url: str,
    detail: str,
    headers: dict[str, str],
    parameters: Any = None,
) -> None:
    response = _request(client, method, url, headers=headers, parameters=parameters)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == detail
