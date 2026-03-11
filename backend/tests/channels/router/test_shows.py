from __future__ import annotations

import uuid
from typing import Any  # noqa: F401

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelOutput,
    ChannelShowsOutput,
)
from app.config import settings
from app.shows.schemas import ShowOutput
from app.sources.schemas import (
    SourceOutput,
)
from tests.channels.utils import create_random_channel, create_random_channel_show
from tests.shows.utils import create_random_show
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import (
    assert_delete,
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_success,
)
from tests.utils.utils import random_lower_string


class TestListChannelShows:
    @staticmethod
    def url(channel: Channel | ChannelOutput) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/shows"

    @staticmethod
    def build_expected(channel: Channel) -> ChannelShowsOutput:
        expected = ChannelShowsOutput()
        for channel_show in channel.shows:
            show = channel_show.show
            source = show.source
            expected.shows.append(ShowOutput.model_validate(show))
            if source.id not in expected.sources:
                expected.sources[source.id] = SourceOutput.model_validate(source)
        return expected

    @pytest.mark.parametrize("show_count", [0, 1, 2])
    def test_list_shows_data(
        self,
        client: TestClient,
        db: Session,
        show_count: int,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=owner.id)
        for _ in range(show_count):
            create_random_channel_show(db, channel)

        result = assert_success(
            client=client,
            method="get",
            url=self.url(channel),
            output_model=ChannelShowsOutput,
            headers=owner.headers,
        )
        expected = self.build_expected(channel)
        assert result.shows == expected.shows
        assert result.sources == expected.sources

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anonymous"])
    def test_list_shows_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        public: bool,
        user_type: str,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=owner.id, public=public)
        show = create_random_show(db, user_id=owner.id, name=random_lower_string())
        create_random_channel_show(db, channel, show=show)

        if user_type == "normal_user" and not public:
            assert_forbidden(
                client=client,
                method="get",
                url=self.url(channel),
                detail="Not authorized to access this Channel",
                headers=create_random_user_alt(client, db).headers,
            )
            return
        if user_type == "anonymous" and not public:
            assert_not_authenticated(
                client=client,
                method="get",
                url=self.url(channel),
            )
            return

        if user_type == "owner":
            headers = owner.headers
        elif user_type == "normal_user":
            headers = create_random_user_alt(client, db).headers
        else:
            headers = {}

        assert_success(
            client=client,
            method="get",
            url=self.url(channel),
            output_model=ChannelShowsOutput,
            headers=headers,
        )

    def test_list_shows_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/shows",
            detail="Channel not found",
            headers=user.headers,
        )


class TestDeleteChannelShow:
    @staticmethod
    def url(channel: Channel | ChannelOutput, show_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/remove-show/{show_id}"

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("model_type", ["owner", "other_owner"])
    def test_remove_show_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        public: bool,
        user_type: str,
        model_type: str,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=owner.id, public=public)
        show = create_random_show(db, user_id=owner.id, name=random_lower_string())
        create_random_channel_show(db, channel, show=show)

        if user_type == "anonymous":
            assert_not_authenticated(
                client=client,
                method="delete",
                url=self.url(channel, show.id),
            )
            return

        if model_type == "owner":
            headers = owner.headers
            assert_delete(
                client=client,
                url=self.url(channel, show.id),
                message=f"{show.name} removed from channel successfully",
                headers=headers,
            )
            return

        headers = create_random_user_alt(client, db).headers
        assert_forbidden(
            client=client,
            method="delete",
            url=self.url(channel, show.id),
            detail="Not authorized to access this Channel",
            headers=headers,
        )

    def test_remove_show_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)

        assert_not_found(
            client=client,
            method="delete",
            url=self.url(channel, uuid.uuid4()),
            detail="Show not found",
            headers=user.headers,
        )

    def test_remove_show_not_in_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        # Create the show on a different channel.
        other_channel_show = create_random_channel_show(db, user_id=user.id)

        assert_not_found(
            client=client,
            method="delete",
            url=self.url(channel, other_channel_show.show_id),
            detail="Show not found in channel",
            headers=user.headers,
        )

    def test_remove_show_channel_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/remove-show/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user.headers,
        )
