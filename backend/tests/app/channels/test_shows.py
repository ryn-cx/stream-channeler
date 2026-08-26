# TODO: Validate


import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import ChannelOutput, ChannelShowsOutput
from app.config import settings
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.route_assertions import (
    assert_delete,
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_success,
)
from tests.app.utils.utils import random_lower_string


# TODO: Validate
class TestListChannelShows:
    # TODO: Validate
    @staticmethod
    def url(channel: Channel | ChannelOutput) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/shows"

    # TODO: Validate
    @staticmethod
    def build_expected(session: Session, channel: Channel) -> ChannelShowsOutput:
        expected = ChannelShowsOutput()
        for channel_show in channel.shows:
            show = channel_show_show(session, channel_show)
            source = show.source
            expected.shows.append(ShowPublic.model_validate(show))
            if source.id not in expected.sources:
                expected.sources[source.id] = SourcePublic.model_validate(source)
        return expected

    # TODO: Validate
    @pytest.mark.parametrize("show_count", [0, 1, 2])
    def test_list_shows_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        show_count: int,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=owner.id)
        for _ in range(show_count):
            create_random_channel_show(session_scoped_session, channel, owner)

        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=self.url(channel),
            output_schema=ChannelShowsOutput,
            headers=owner_headers,
        )
        expected = self.build_expected(session_scoped_session, channel)
        assert result.shows == expected.shows
        assert result.sources == expected.sources

    # TODO: Validate
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anonymous"])
    def test_list_shows_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_type: str,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=owner.id,
            is_public=record_is_public,
        )
        show = create_random_show(
            session_scoped_session,
            owner.id,
            name=random_lower_string(),
        )
        create_random_channel_show(session_scoped_session, channel, show)

        if user_type == "normal_user" and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.url(channel),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return
        if user_type == "anonymous" and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.url(channel),
            )
            return

        if user_type == "owner":
            headers = owner_headers
        elif user_type == "normal_user":
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        assert_success(
            client=session_scoped_client,
            method="get",
            url=self.url(channel),
            output_schema=ChannelShowsOutput,
            headers=headers,
        )

    # TODO: Validate
    def test_list_shows_not_found(
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
            method="get",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/shows",
            detail="Channel not found",
            headers=user_headers,
        )


# TODO: Validate
class TestDeleteChannelShow:
    # TODO: Validate
    @staticmethod
    def url(channel: Channel | ChannelOutput, show_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/remove-show/{show_id}"

    # TODO: Validate
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_remove_show_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=owner.id,
            is_public=record_is_public,
        )
        show = create_random_show(
            session_scoped_session,
            owner.id,
            name=random_lower_string(),
        )
        create_random_channel_show(session_scoped_session, channel, show)

        if not user_is_authenticated:
            assert_not_authenticated(
                client=session_scoped_client,
                method="delete",
                url=self.url(channel, show.id),
            )
            return

        if user_is_owner:
            assert_delete(
                client=session_scoped_client,
                url=self.url(channel, show.id),
                message=f"{show.name} removed from channel successfully",
                headers=owner_headers,
            )
            return

        other_user = create_random_user(session_scoped_session)
        other_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=other_user.email,
            session=session_scoped_session,
        )
        assert_forbidden(
            client=session_scoped_client,
            method="delete",
            url=self.url(channel, show.id),
            detail="Not authorized to access this Channel",
            headers=other_headers,
        )

    # TODO: Validate
    def test_remove_show_not_found(
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
        channel = create_random_channel(session_scoped_session, user=user.id)

        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=self.url(channel, uuid.uuid4()),
            detail="Show not found",
            headers=user_headers,
        )

    # TODO: Validate
    def test_remove_show_not_in_channel(
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
        channel = create_random_channel(session_scoped_session, user=user.id)
        # Create the show on a different channel. The show must be owned by the
        # user, otherwise readable_record raises 403 (the randomly generated
        # plugin can be private and owned by someone else) before the channel
        # membership check is reached.
        other_channel = create_random_channel(session_scoped_session, user=user.id)
        other_channel_show = create_random_channel_show(
            session_scoped_session,
            other_channel,
            user,
        )

        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=self.url(
                channel,
                channel_show_show(session_scoped_session, other_channel_show).id,
            ),
            detail="Show was not found on channel",
            headers=user_headers,
        )

    # TODO: Validate
    def test_remove_show_channel_not_found(
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
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/remove-show/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user_headers,
        )
