# TODO: This was completely AI generated just to have a temporary baseline and should be
# replaced with real tests.


import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel, URLStatus
from app.channels.schemas import ChannelQueueOutput
from app.config import settings
from tests.app.channels.base import BaseChannelSubEndpointTests
from tests.app.channels.utils import create_random_channel_queue
from tests.app.utils.route_assertions import (
    assert_delete,
    assert_not_found,
    assert_success_list,
)
from tests.app.utils.utils import random_lower_string


@pytest.fixture(autouse=True)
def _mock_background_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the queue endpoints from launching a real background import in these tests.

    The importer itself is exercised directly in test_import_queue.py.
    """
    monkeypatch.setattr("app.channels.router.run_import_in_background", lambda: None)


class BaseChannelQueueTests(BaseChannelSubEndpointTests):
    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # TODO: record_is_public is required by the base signature but unused here.
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def queue_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/import-queue"

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return self.queue_url(channel_id)

    def queue_parameters(self) -> list[str] | None:
        return None

    def assert_queue_contents(
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        expected_urls: list[str],
    ) -> None:
        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=self.queue_url(channel.id),
            output_schema=ChannelQueueOutput,
            headers=headers,
        )
        assert [record.url for record in result] == expected_urls

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
            url=self.queue_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=initial_test_data.headers,
            parameters=self.queue_parameters(),
        )


class TestQueueGet(BaseChannelQueueTests):
    sub_http_method = "get"

    def test_get_queue(
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
        queue_entry_1 = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        queue_entry_2 = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[queue_entry_2.url, queue_entry_1.url],
        )

    def test_get_queue_empty(
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

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[],
        )


class TestQueueAddURL(BaseChannelQueueTests):
    sub_http_method = "post"
    # TODO: annotate as ClassVar (or set in __init__) instead of a mutable default.
    sub_parameters = ["placeholder"]  # noqa: RUF012

    def queue_parameters(self) -> list[str]:
        return [random_lower_string()]

    def assert_add_urls(
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        urls: list[str],
        expected_urls: list[str],
    ) -> None:
        assert_success_list(
            client=session_scoped_client,
            method="post",
            url=self.queue_url(channel.id),
            output_schema=ChannelQueueOutput,
            headers=headers,
            parameters=urls,
        )
        self.assert_queue_contents(
            session_scoped_client,
            channel,
            headers,
            expected_urls,
        )

    @pytest.mark.parametrize("initial_url_count", [0, 1, 2])
    @pytest.mark.parametrize("new_url_count", [0, 1, 2])
    def test_append_urls(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_url_count: int,
        new_url_count: int,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        initial_urls = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
            ).url
            for _ in range(initial_url_count)
        ]

        new_urls = [random_lower_string() for _ in range(new_url_count)]
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=new_urls,
            expected_urls=new_urls[::-1] + initial_urls[::-1],
        )

    def test_append_existing_url(
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
        existing = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )

    def test_append_duplicate_urls(
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
        random_url = random_lower_string()
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[random_url, random_url],
            expected_urls=[random_url],
        )

    def test_append_duplicate_existing_url(
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
        existing = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )


class TestQueueDeleteURL(BaseChannelQueueTests):
    sub_http_method = "delete"

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel_id)}/{uuid.uuid4()}"

    def queue_entry_url(self, channel: Channel, entry_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel.id)}/{entry_id}"

    def test_delete_url(
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
        queue_entries = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
            )
            for _ in range(3)
        ]

        for queue_entry in queue_entries:
            assert_delete(
                client=session_scoped_client,
                url=self.queue_entry_url(initial_test_data.record, queue_entry.id),
                message=f"{queue_entry.url} removed from import queue successfully",
                headers=initial_test_data.headers,
            )

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[],
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
            method="delete",
            url=self.queue_entry_url(initial_test_data.record, uuid.uuid4()),
            detail="URL not found",
            headers=initial_test_data.headers,
        )


class TestClearCompletedQueue(BaseChannelSubEndpointTests):
    sub_http_method = "delete"

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # TODO: record_is_public is required by the base signature but unused here.
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

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
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_statuses: list[URLStatus],
        expected_remaining: list[URLStatus],
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        records = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
                status=s,
            )
            for s in initial_statuses
        ]

        response = session_scoped_client.delete(
            self.sub_url(initial_test_data.record.id),
            headers=initial_test_data.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Import queue cleared successfully"

        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/import-queue",
            output_schema=ChannelQueueOutput,
            headers=initial_test_data.headers,
        )
        remaining_urls = {record.url for record in result}
        expected_urls = {
            r.url
            for r, s in zip(records, initial_statuses, strict=True)
            if s in expected_remaining
        }
        assert remaining_urls == expected_urls
