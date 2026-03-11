# TODO: Validate
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelOutput,
    EpisodeWithExtrasOutput,
)
from app.config import settings
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowOutput
from app.sources.schemas import SourceOutput
from tests.channels.utils import create_random_channel, create_random_channel_show
from tests.episodes.utils import create_random_episode
from tests.plugins.utils import create_random_plugin
from tests.users.utils import CreatedUser, create_random_user_alt
from tests.utils.route_assertions import (
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
)


class TestChannelEpisodes:
    @staticmethod
    def url(channel: Channel | ChannelOutput) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/episodes"

    @staticmethod
    def create_channel_with_episodes(
        db: Session,
        user: CreatedUser,
        *,
        public: bool,
    ) -> tuple[Channel, ChannelEpisodesOutput]:
        channel = create_random_channel(db, user_id=user.id, public=public)

        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )
        expected.channels[channel.id] = ChannelOutput.model_validate(channel)

        for _ in range(2):
            plugin = create_random_plugin(db, user_id=user.id, public=True)
            channel_show = create_random_channel_show(
                db,
                channel,
                plugin=plugin,
                white_list_mode=False,
            )
            show = channel_show.show
            create_random_episode(db, show=show)
            source = show.source
            plugin = source.plugin
            season = show.seasons[0]
            episode = season.episodes[0]

            expected.episodes.append(
                EpisodeWithExtrasOutput(**episode.model_dump(), channel_id=channel.id),
            )
            expected.seasons[season.id] = SeasonOutput.model_validate(season)
            expected.shows[show.id] = ShowOutput.model_validate(show)
            expected.sources[source.id] = SourceOutput.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)

        return channel, expected

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

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anon"])
    def test_with_episodes(
        self,
        client: TestClient,
        db: Session,
        *,
        public: bool,
        user_type: str,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel, expected = self.create_channel_with_episodes(db, owner, public=public)
        if user_type == "normal_user" and not public:
            assert_forbidden(
                client=client,
                method="get",
                url=self.url(channel),
                detail="Not authorized to access this Channel",
                headers=create_random_user_alt(client, db).headers,
            )
            return
        if user_type == "anon" and not public:
            assert_not_authenticated(client=client, method="get", url=self.url(channel))
            return
        if user_type == "owner":
            headers = owner.headers
        elif user_type == "normal_user":
            headers = create_random_user_alt(client, db).headers
        else:
            headers = {}
        response = client.get(self.url(channel), headers=headers)
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        self.assert_episodes(response_data, expected)

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anon"])
    def test_no_episodes(
        self,
        client: TestClient,
        db: Session,
        *,
        public: bool,
        user_type: str,
    ) -> None:
        owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=owner.id, public=public)
        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )
        if user_type == "normal_user" and not public:
            assert_forbidden(
                client=client,
                method="get",
                url=self.url(channel),
                detail="Not authorized to access this Channel",
                headers=create_random_user_alt(client, db).headers,
            )
            return
        if user_type == "anon" and not public:
            assert_not_authenticated(client=client, method="get", url=self.url(channel))
            return
        if user_type == "owner":
            headers = owner.headers
        elif user_type == "normal_user":
            headers = create_random_user_alt(client, db).headers
        else:
            headers = {}
        response = client.get(self.url(channel), headers=headers)
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        assert response_data == expected

    @pytest.mark.parametrize(
        "user_type",
        ["owner", "plugin_owner", "normal_user", "anon"],
    )
    def test_private_plugin_visibility(
        self,
        client: TestClient,
        db: Session,
        user_type: str,
    ) -> None:
        """Episodes from private plugins should only be visible to the plugin owner."""
        channel_owner = create_random_user_alt(client, db)
        plugin_owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=channel_owner.id, public=True)

        # Add a show from a private plugin owned by plugin_owner
        private_plugin = create_random_plugin(
            db,
            user_id=plugin_owner.id,
            public=False,
        )
        channel_show = create_random_channel_show(
            db,
            channel,
            plugin=private_plugin,
            white_list_mode=False,
        )
        show = channel_show.show
        create_random_episode(db, show=show)

        if user_type == "owner":
            headers = channel_owner.headers
        elif user_type == "plugin_owner":
            headers = plugin_owner.headers
        elif user_type == "normal_user":
            headers = create_random_user_alt(client, db).headers
        else:
            headers = {}

        response = client.get(self.url(channel), headers=headers)
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

    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anon"])
    def test_public_plugin_visibility(
        self,
        client: TestClient,
        db: Session,
        user_type: str,
    ) -> None:
        """Episodes from public plugins should be visible to all channel user_types."""
        channel_owner = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=channel_owner.id, public=True)

        public_plugin = create_random_plugin(
            db,
            user_id=channel_owner.id,
            public=True,
        )
        channel_show = create_random_channel_show(
            db,
            channel,
            plugin=public_plugin,
            white_list_mode=False,
        )
        show = channel_show.show
        create_random_episode(db, show=show)

        if user_type == "owner":
            headers = channel_owner.headers
        elif user_type == "normal_user":
            headers = create_random_user_alt(client, db).headers
        else:
            headers = {}

        response = client.get(self.url(channel), headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = ChannelEpisodesOutput.model_validate(response.json())
        assert len(data.episodes) == 1

    def test_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/episodes",
            detail="Channel not found",
            headers=user.headers,
        )
