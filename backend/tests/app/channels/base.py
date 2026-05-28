# TODO: Validate


import uuid
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import ChannelCreate, ChannelOutput, ChannelUpdate
from app.models import Visibility
from tests.app.channels.utils import create_random_channel
from tests.app.utils.base import BaseTests
from tests.app.utils.route_assertions import Method, assert_not_found, make_request


class ChannelTestMixin(BaseTests[Channel]):
    database_model = Channel
    create_schema = ChannelCreate
    output_schema = ChannelOutput
    update_schema = ChannelUpdate
    create_record_function = staticmethod(create_random_channel)

    # Channels do not rely on plugins for visibility and instead have their own
    # visibility column.
    def set_visibility(self, record: Channel, *, record_is_public: bool) -> None:
        record.visibility = (
            Visibility.public if record_is_public else Visibility.private
        )


class BaseChannelSubEndpointTests(ChannelTestMixin):
    sub_http_method: Method
    sub_parameters: dict[str, Any] | list[Any] | None = None

    def sub_url(self, channel_id: uuid.UUID) -> str:
        raise NotImplementedError

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return (user_is_authenticated and user_is_owner) or record_is_public

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_get_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        url = self.sub_url(initial_test_data.record.id)
        if self.can_access_sub_endpoint(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            response = make_request(
                session_scoped_client,
                self.sub_http_method,
                url,
                headers=initial_test_data.headers,
                parameters=self.sub_parameters,
            )
            assert response.status_code not in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method=self.sub_http_method,
                url=url,
                model_name=self.model_name,
                headers=initial_test_data.headers,
            )

    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        assert_not_found(
            client=session_scoped_client,
            method=self.sub_http_method,
            url=self.sub_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=initial_test_data.headers,
            parameters=self.sub_parameters,
        )
