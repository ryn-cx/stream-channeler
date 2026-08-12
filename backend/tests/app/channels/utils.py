# TODO: Validate
import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.channels import service
from app.channels.models import ChannelQueue, URLStatus
from app.channels.schemas import ChannelCreate
from app.config import settings
from app.models import Visibility
from app.tools.import_queue import import_queue
from app.users.models import User


# TODO: Validate
def create_channel(session: Session, user: User) -> str:
    channel = service.create_channel(
        session,
        user,
        ChannelCreate(visibility=Visibility.private, anonymous=False),
    )
    return str(channel.id)


# TODO: Validate
def import_url(
    client: TestClient,
    session: Session,
    headers: dict[str, str],
    channel_id: str,
    url: str,
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/channels/{channel_id}/import-queue",
        headers=headers,
        json=[url],
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    import_queue(session)

    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.channel_id == uuid.UUID(channel_id)),
    ).one()
    assert queue_entry.status == URLStatus.IMPORTED, queue_entry.note


# TODO: Validate
def whitelist_every_season(
    client: TestClient,
    headers: dict[str, str],
    channel_id: str,
) -> int:
    shows_response = client.get(
        f"{settings.API_V1_STR}/channels/{channel_id}/shows",
        headers=headers,
    )
    assert shows_response.status_code == status.HTTP_200_OK, shows_response.text
    show_id = shows_response.json()["shows"][0]["id"]

    whitelist_response = client.get(
        f"{settings.API_V1_STR}/channels/{channel_id}/whitelist/{show_id}",
        headers=headers,
    )
    assert whitelist_response.status_code == status.HTTP_200_OK, whitelist_response.text
    seasons = whitelist_response.json()["seasons"]

    update_response = client.patch(
        f"{settings.API_V1_STR}/channels/{channel_id}/whitelist/{show_id}",
        headers=headers,
        json={
            "is_whitelist": True,
            "seasons": [{"id": season["id"], "marked": True} for season in seasons],
        },
    )
    assert update_response.status_code == status.HTTP_200_OK, update_response.text
    assert all(season["filtered"] for season in update_response.json()["seasons"])
    return len(seasons)
