# TODO: Validate
import uuid
from functools import partial

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import ChannelQueuesListOutput
from app.config import settings
from tests.channels.router import BaseChannelSubEndpointTests
from tests.channels.utils import (
    create_random_channel,
    create_random_channel_queue,
)
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import (
    Method,
    assert_delete,
    assert_not_found,
    assert_success,
)
from tests.utils.utils import random_lower_string


def assert_queue_list_response(
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
        output_model=ChannelQueuesListOutput,
        headers=headers,
        parameters=parameters,
    )


class BaseChannelQueueTests(BaseChannelSubEndpointTests):
    def queue_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/import-queue"

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return self.queue_url(channel_id)

    def queue_parameters(self) -> list[str] | None:
        return None

    def assert_queue_contents(
        self,
        client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        expected_urls: list[str],
    ) -> None:
        result = assert_success(
            client=client,
            method="get",
            url=self.queue_url(channel.id),
            output_model=ChannelQueuesListOutput,
            headers=headers,
        )
        assert [entry.url for entry in result.data] == expected_urls

    def test_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method=self.sub_http_method,
            url=self.queue_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=user.headers,
            parameters=self.queue_parameters(),
        )


class TestQueueGet(BaseChannelQueueTests):
    sub_http_method = "get"
    sub_assert_response = staticmethod(assert_queue_list_response)

    def test_get_queue(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        queue_entry_1 = create_random_channel_queue(db, channel)
        queue_entry_2 = create_random_channel_queue(db, channel)

        self.assert_queue_contents(
            client,
            channel,
            user.headers,
            expected_urls=[queue_entry_2.url, queue_entry_1.url],
        )

    def test_get_queue_empty(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)

        self.assert_queue_contents(
            client,
            channel,
            user.headers,
            expected_urls=[],
        )


class TestQueueAddURL(BaseChannelQueueTests):
    sub_http_method = "post"
    sub_assert_response = staticmethod(assert_queue_list_response)
    sub_parameters = ["placeholder"]

    def queue_parameters(self) -> list[str]:
        return [random_lower_string()]

    def assert_add_urls(
        self,
        client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        urls: list[str],
        expected_urls: list[str],
    ) -> None:
        assert_success(
            client=client,
            method="post",
            url=self.queue_url(channel.id),
            output_model=ChannelQueuesListOutput,
            headers=headers,
            parameters=urls,
        )
        self.assert_queue_contents(client, channel, headers, expected_urls)

    @pytest.mark.parametrize("initial_url_count", [0, 1, 2])
    @pytest.mark.parametrize("new_url_count", [0, 1, 2])
    def test_append_urls(
        self,
        client: TestClient,
        db: Session,
        initial_url_count: int,
        new_url_count: int,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)

        initial_urls = [
            create_random_channel_queue(db, channel).url
            for _ in range(initial_url_count)
        ]

        new_urls = [random_lower_string() for _ in range(new_url_count)]
        self.assert_add_urls(
            client,
            channel,
            user.headers,
            urls=new_urls,
            expected_urls=new_urls[::-1] + initial_urls[::-1],
        )

    def test_append_existing_url(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        existing = create_random_channel_queue(db, channel)
        self.assert_add_urls(
            client,
            channel,
            user.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )

    def test_append_duplicate_urls(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        random_url = random_lower_string()
        self.assert_add_urls(
            client,
            channel,
            user.headers,
            urls=[random_url, random_url],
            expected_urls=[random_url],
        )

    def test_append_duplicate_existing_url(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        existing = create_random_channel_queue(db, channel)
        self.assert_add_urls(
            client,
            channel,
            user.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )


class TestQueueDeleteURL(BaseChannelQueueTests):
    sub_http_method = "delete"
    sub_assert_response = staticmethod(
        partial(assert_not_found, detail="URL not found"),
    )

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel_id)}/{uuid.uuid4()}"

    def queue_entry_url(self, channel: Channel, entry_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel.id)}/{entry_id}"

    def test_delete_url(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        queue_entries = [create_random_channel_queue(db, channel) for _ in range(3)]

        for queue_entry in queue_entries:
            assert_delete(
                client=client,
                url=self.queue_entry_url(channel, queue_entry.id),
                message=f"{queue_entry.url} removed from import queue successfully",
                headers=user.headers,
            )

        self.assert_queue_contents(
            client,
            channel,
            user.headers,
            expected_urls=[],
        )

    def test_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)

        assert_not_found(
            client=client,
            method="delete",
            url=self.queue_entry_url(channel, uuid.uuid4()),
            detail="URL not found",
            headers=user.headers,
        )
