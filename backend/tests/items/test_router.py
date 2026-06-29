import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from tests.utils.item import create_random_item


def test_create_item(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    data = {"title": "Foo", "description": "Fighters"}
    response = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert "id" in content
    assert "owner_id" in content


def test_read_item(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    assert content["title"] == item.title
    assert content["description"] == item.description
    assert content["id"] == str(item.id)
    assert content["owner_id"] == str(item.owner_id)


def test_read_item_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    content = response.json()
    assert content["detail"] == "Item not found"


def test_read_item_not_enough_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_read_items(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    create_random_item(db)
    create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    expected_number_of_items = 2
    assert len(content["data"]) >= expected_number_of_items


def test_read_items_server_side_filtering(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = create_random_item(db)
    create_random_item(db)
    monkeypatch.setattr("app.service.SERVER_SIDE_THRESHOLD", 0)

    response = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"filter_options": f'[{{"id": "title", "value": "{item.title}"}}]'},
    )

    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    assert content["is_server_side"] is True
    assert content["filtered_count"] == 1
    assert [row["id"] for row in content["data"]] == [str(item.id)]


def test_read_items_server_side_sorting(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_random_item(db)
    create_random_item(db)
    create_random_item(db)
    monkeypatch.setattr("app.service.SERVER_SIDE_THRESHOLD", 0)

    ascending = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"sort_options": '[{"id": "title", "desc": false}]'},
    )
    assert ascending.status_code == status.HTTP_200_OK
    ascending_content = ascending.json()
    assert ascending_content["is_server_side"] is True
    ascending_titles = [item["title"] for item in ascending_content["data"]]
    assert ascending_titles == sorted(ascending_titles, key=str.casefold)

    descending = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"sort_options": '[{"id": "title", "desc": true}]'},
    )
    assert descending.status_code == status.HTTP_200_OK
    descending_titles = [item["title"] for item in descending.json()["data"]]
    assert descending_titles == sorted(descending_titles, key=str.casefold, reverse=True)


def test_read_items_server_side_paginates(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_random_item(db)
    create_random_item(db)
    monkeypatch.setattr("app.service.SERVER_SIDE_THRESHOLD", 0)
    sort_options = '[{"id": "title", "desc": false}]'

    first_page = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"sort_options": sort_options, "offset": 0, "limit": 1},
    ).json()
    second_page = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"sort_options": sort_options, "offset": 1, "limit": 1},
    ).json()

    assert first_page["is_server_side"] is True
    assert len(first_page["data"]) == 1
    assert len(second_page["data"]) == 1
    assert first_page["data"][0]["id"] != second_page["data"][0]["id"]
    first_title = first_page["data"][0]["title"]
    second_title = second_page["data"][0]["title"]
    assert [first_title, second_title] == sorted(
        [first_title, second_title],
        key=str.casefold,
    )


def test_update_item(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert content["id"] == str(item.id)
    assert content["owner_id"] == str(item.owner_id)


def test_update_item_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    content = response.json()
    assert content["detail"] == "Item not found"


def test_update_item_not_enough_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_delete_item(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    response = client.delete(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.json()
    assert content["message"] == "Item deleted successfully"


def test_delete_item_not_found(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    content = response.json()
    assert content["detail"] == "Item not found"


def test_delete_item_not_enough_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    item = create_random_item(db)
    response = client.delete(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    content = response.json()
    assert content["detail"] == "Not enough permissions"
