# TODO: Validate
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import ChannelOutput, ChannelPatchInput, ChannelPostInput
from tests.channels.utils import create_random_channel
from tests.users.utils import create_random_user_alt
from tests.utils.base import BaseTests
from tests.utils.route_assertions import (
    Method,
    assert_not_found,
)


class ChannelTestMixin(BaseTests[Channel]):
    database_model = Channel
    input_schema = ChannelPostInput
    output_model = ChannelOutput
    patch_model = ChannelPatchInput

    create_record_function = staticmethod(create_random_channel)


class BaseChannelSubEndpointTests(ChannelTestMixin):
    sub_http_method: Method
    sub_assert_response: Callable[..., None]
    sub_parameters: dict[str, Any] | list[Any] | None = None

    def sub_url(self, channel_id: uuid.UUID) -> str:
        raise NotImplementedError

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        is_owner: bool,
        public: bool,
    ) -> None:
        authenticated = user_type != "anonymous"

        setup = self.create_test_data(
            client,
            db,
            is_owner=is_owner,
            authenticated=authenticated,
            public=public,
        )

        if self.assert_write_permission(
            db,
            client,
            authenticated=authenticated,
            is_owner=is_owner,
            method=self.sub_http_method,
            url=self.sub_url(setup.record.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=setup.headers,
            parameters=self.sub_parameters,
        ):
            self.sub_assert_response(
                client=client,
                method=self.sub_http_method,
                url=self.sub_url(setup.record.id),
                headers=setup.headers,
                parameters=self.sub_parameters,
            )

    def test_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method=self.sub_http_method,
            url=self.sub_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=user.headers,
            parameters=self.sub_parameters,
        )
