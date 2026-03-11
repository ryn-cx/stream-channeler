# TODO: Validate
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import URLStatus
from app.channels.schemas import ChannelQueuesListOutput
from app.config import settings
from app.models import Message
from tests.channels.router import BaseChannelSubEndpointTests
from tests.channels.utils import (
    create_random_channel,
    create_random_channel_queue,
)
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import (
    Method,
    assert_success,
)


def assert_message_response(
    client: TestClient,
    method: Method,
    url: str,
    headers: dict[str, str] | None = None,
    parameters: dict[str, object] | list[object] | None = None,
) -> None:
    assert_success(
        client=client,
        method=method,
        url=url,
        output_model=Message,
        headers=headers,
        parameters=parameters,
    )


class TestClearCompletedQueue(BaseChannelSubEndpointTests):
    sub_http_method = "delete"
    sub_assert_response = staticmethod(assert_message_response)

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/clear-completed-import-queue"

    @pytest.mark.parametrize(
        ("initial_statuses", "expected_remaining"),
        [
            (
                [URLStatus.IMPORTED, URLStatus.IMPORTED, URLStatus.PENDING],
                [URLStatus.PENDING],
            ),
            (
                [URLStatus.PENDING, URLStatus.FAILED],
                [URLStatus.PENDING, URLStatus.FAILED],
            ),
            ([], []),
        ],
        ids=["with_completed", "no_completed", "empty"],
    )
    def test_clear_completed(
        self,
        client: TestClient,
        db: Session,
        initial_statuses: list[URLStatus],
        expected_remaining: list[URLStatus],
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        entries = [
            create_random_channel_queue(db, channel, status=s) for s in initial_statuses
        ]

        response = client.delete(self.sub_url(channel.id), headers=user.headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Import queue cleared successfully"

        result = assert_success(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
            output_model=ChannelQueuesListOutput,
            headers=user.headers,
        )
        remaining_urls = {entry.url for entry in result.data}
        expected_urls = {
            e.url
            for e, s in zip(entries, initial_statuses, strict=True)
            if s in expected_remaining
        }
        assert remaining_urls == expected_urls
