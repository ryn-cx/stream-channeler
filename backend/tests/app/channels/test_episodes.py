# TODO: Validate


import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelEpisodesOutput,
    EpisodeWithDetails,
)
from app.channels.service import channel_output
from app.config import settings
from app.models import Visibility
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.models import User
from tests.app.channels.base import BaseChannelSubEndpointTests
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.plugins.utils import create_random_plugin
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.route_assertions import assert_forbidden, assert_not_authenticated


# TODO: Validate
class TestChannelEpisodes(BaseChannelSubEndpointTests):
    sub_http_method = "get"
    sub_parameters = None

    # TODO: Validate
    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/episodes"

    # TODO: Validate
    @pytest.mark.skip(reason="Covered by test_with_episodes and test_no_episodes")
    def test_get_permissions(self) -> None:  # type: ignore[override]
        pass

    # TODO: Validate
    def generic_record_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/channels/{record_id}/episodes"

    # TODO: Validate
    @staticmethod
    def create_channel_with_episodes(
        session_scoped_session: Session,
        user_id: uuid.UUID,
        *,
        is_public: bool,
    ) -> tuple[Channel, ChannelEpisodesOutput]:
        channel = create_random_channel(
            session_scoped_session,
            user=user_id,
            is_public=is_public,
        )

        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )
        for _ in range(2):
            plugin = create_random_plugin(
                session_scoped_session,
                user_id,
                visibility=Visibility.public,
            )
            channel_show = create_random_channel_show(
                session_scoped_session,
                channel,
                plugin,
                is_whitelist=False,
            )
            show = channel_show_show(session_scoped_session, channel_show)
            create_random_episode(session_scoped_session, show)
            source = show.source
            plugin = source.plugin
            season = show.seasons[0]
            episode = season.episodes[0]

            expected.episodes.append(
                EpisodeWithDetails(
                    **episode.model_dump(),
                    channel_id=channel.id,
                    channel_ids=[channel.id],
                ),
            )
            expected.seasons[season.id] = SeasonOutput.model_validate(season)
            expected.shows[show.id] = ShowPublic.model_validate(show)
            expected.sources[source.id] = SourcePublic.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)

        return channel, expected

    # TODO: Validate
    @staticmethod
    def assert_episodes(
        response_data: ChannelEpisodesOutput,
        expected: ChannelEpisodesOutput,
    ) -> None:
        response_data.episodes.sort(key=lambda e: e.id)
        expected.episodes.sort(key=lambda e: e.id)
        assert response_data.episodes == expected.episodes
        assert response_data.seasons == expected.seasons
        assert response_data.shows == expected.shows
        assert response_data.sources == expected.sources
        assert response_data.plugins == expected.plugins
        assert response_data.channels == expected.channels
        assert response_data == expected

    # TODO: Validate
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_with_episodes(
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
        channel, expected = self.create_channel_with_episodes(
            session_scoped_session,
            owner.id,
            is_public=record_is_public,
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
            )
            return
        if user_is_authenticated and not user_is_owner and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return

        viewer: User | None
        if user_is_owner:
            headers = owner_headers
            viewer = owner
        elif user_is_authenticated:
            viewer = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=viewer.email,
                session=session_scoped_session,
            )
        else:
            headers = {}
            viewer = None
        # An anonymous channel hides its owner from everyone but them, so who is
        # reading it decides what the channel reads as.
        expected.channels[channel.id] = channel_output(channel, viewer)
        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        self.assert_episodes(response_data, expected)

    # TODO: Validate
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_no_episodes(
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
        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
            )
            return
        if user_is_authenticated and not user_is_owner and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return

        if user_is_owner:
            headers = owner_headers
        elif user_is_authenticated:
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}
        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        assert response_data == expected

    # TODO: Validate
    @pytest.mark.parametrize(
        "user_type",
        ["owner", "plugin_owner", "normal_user", "anon"],
    )
    def test_private_plugin_visibility(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        user_type: str,
    ) -> None:
        """Episodes from private plugins should only be visible to the plugin owner."""
        channel_owner = create_random_user(session_scoped_session)
        channel_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=channel_owner.email,
            session=session_scoped_session,
        )
        plugin_owner = create_random_user(session_scoped_session)
        plugin_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=plugin_owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=channel_owner.id,
            is_public=True,
        )

        # Add a show from a private plugin owned by plugin_owner
        private_plugin = create_random_plugin(
            session_scoped_session,
            plugin_owner.id,
            visibility=Visibility.private,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            private_plugin,
            is_whitelist=False,
        )
        show = channel_show_show(session_scoped_session, channel_show)
        create_random_episode(session_scoped_session, show)

        if user_type == "owner":
            headers = channel_owner_headers
        elif user_type == "plugin_owner":
            headers = plugin_owner_headers
        elif user_type == "normal_user":
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = ChannelEpisodesOutput.model_validate(response.json())

        if user_type == "plugin_owner":
            assert len(data.episodes) == 1
            assert len(data.seasons) == 1
            assert len(data.shows) == 1
            assert len(data.sources) == 1
            assert len(data.plugins) == 1
            assert len(data.channels) == 1
        else:
            assert not data.episodes
            assert not data.seasons
            assert not data.shows
            assert not data.sources
            assert not data.plugins
            assert not data.channels

    # TODO: Validate
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_public_plugin_visibility(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        """Episodes from public plugins should be visible to all users."""
        channel_owner = create_random_user(session_scoped_session)
        channel_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=channel_owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=channel_owner.id,
            is_public=True,
        )

        public_plugin = create_random_plugin(
            session_scoped_session,
            channel_owner.id,
            visibility=Visibility.public,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            public_plugin,
            is_whitelist=False,
        )
        show = channel_show_show(session_scoped_session, channel_show)
        create_random_episode(session_scoped_session, show)

        if user_is_owner:
            headers = channel_owner_headers
        elif user_is_authenticated:
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = ChannelEpisodesOutput.model_validate(response.json())
        assert len(data.episodes) == 1
