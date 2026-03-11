import uuid
from typing import Literal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.schemas import ChannelMediaFilter, ChannelOutput
from app.config import settings
from tests.channels.utils import create_random_channel
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import (
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
)
from tests.utils.utils import dump_random_model


class TestUpdateDefaultOrder:
    @staticmethod
    def url(channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/default-order"

    def assert_update(
        self,
        client: TestClient,
        channel_id: uuid.UUID,
        headers: dict[str, str],
        mode: Literal["minimal", "full"],
    ) -> ChannelOutput:
        response = client.patch(
            self.url(channel_id),
            json=dump_random_model(ChannelMediaFilter, mode),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        return ChannelOutput.model_validate(response.json())

    @pytest.mark.parametrize("initial_mode", ["minimal", "full"])
    @pytest.mark.parametrize("update_mode", ["minimal", "full"])
    def test_update_default_order(
        self,
        client: TestClient,
        db: Session,
        initial_mode: Literal["minimal", "full"],
        update_mode: Literal["minimal", "full"],
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)

        self.assert_update(client, channel.id, user.headers, initial_mode)
        self.assert_update(client, channel.id, user.headers, update_mode)

    @pytest.mark.parametrize("user_type", ["normal_user", "anon"])
    def test_update_default_order_errors(
        self,
        client: TestClient,
        db: Session,
        user_type: str,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=owner.id)

        if user_type == "normal_user":
            assert_forbidden(
                client=client,
                method="patch",
                url=self.url(channel.id),
                detail="Not authorized to access this Channel",
                headers=create_random_user_alt(client, db).headers,
            )
        else:
            assert_not_authenticated(
                client=client,
                method="patch",
                url=self.url(channel.id),
            )

    def test_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="patch",
            url=self.url(uuid.uuid4()),
            detail="Channel not found",
            headers=user.headers,
        )
