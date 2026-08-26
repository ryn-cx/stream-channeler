# TODO: Validate


import uuid
from typing import Literal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.schemas import ChannelOptions, ChannelOutput
from app.config import settings
from tests.app.channels.utils import create_random_channel
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.route_assertions import (
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
)
from tests.app.utils.utils import dump_random_model


# TODO: Validate
class TestUpdateDefaultOrder:
    # TODO: Validate
    @staticmethod
    def url(channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/default-order"

    # TODO: Validate
    def assert_update(
        self,
        session_scoped_client: TestClient,
        channel_id: uuid.UUID,
        headers: dict[str, str],
        mode: Literal["minimal", "full"],
    ) -> ChannelOutput:
        response = session_scoped_client.patch(
            self.url(channel_id),
            json=dump_random_model(ChannelOptions, mode),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        return ChannelOutput.model_validate(response.json())

    # TODO: Validate
    @pytest.mark.parametrize("initial_mode", ["minimal", "full"])
    @pytest.mark.parametrize("update_mode", ["minimal", "full"])
    def test_update_default_order(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_mode: Literal["minimal", "full"],
        update_mode: Literal["minimal", "full"],
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=user.id)

        self.assert_update(
            session_scoped_client,
            channel.id,
            user_headers,
            initial_mode,
        )
        self.assert_update(session_scoped_client, channel.id, user_headers, update_mode)

    # TODO: Validate
    @pytest.mark.parametrize("user_type", ["normal_user", "anon"])
    def test_update_default_order_errors(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        user_type: str,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=owner.id)

        if user_type == "normal_user":
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="patch",
                url=self.url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
        else:
            assert_not_authenticated(
                client=session_scoped_client,
                method="patch",
                url=self.url(channel.id),
            )

    # TODO: Validate
    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        assert_not_found(
            client=session_scoped_client,
            method="patch",
            url=self.url(uuid.uuid4()),
            detail="Channel not found",
            headers=user_headers,
        )
