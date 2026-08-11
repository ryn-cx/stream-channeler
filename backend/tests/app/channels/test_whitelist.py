# TODO: Validate


import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel, ChannelShow
from app.channels.schemas import (
    ChannelShowsOutput,
    WhitelistEntryInput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.channels.service import update_whitelist
from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.models import Visibility
from app.shows.models import Show
from app.users.models import User
from tests.app.channels.base import BaseChannelSubEndpointTests
from tests.app.channels.utils import channel_show_show, create_random_channel_show
from tests.app.episodes.utils import create_random_episode
from tests.app.plugins.utils import create_random_plugin
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import create_random_user
from tests.app.utils.route_assertions import assert_forbidden, assert_success


# TODO: Validate
class TestGetWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "get"

    # TODO: Validate
    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # TODO: record_is_public is required by the base signature but unused here.
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

    # TODO: Validate
    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    # TODO: reduce parameter count, e.g. group args into a params/dataclass object.
    # TODO: Validate
    def assert_whitelist_success(  # noqa: PLR0913
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        channel_show: ChannelShow,
        show: Show,
        episodes: list[Episode],
        headers: dict[str, str],
        *,
        expected_season_ids: list[uuid.UUID] | None = None,
        expected_episode_ids: list[uuid.UUID] | None = None,
    ) -> None:
        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/whitelist/{show.id}",
            output_schema=WhitelistShowOutput,
            headers=headers,
        )
        assert result.is_whitelist == channel_show.is_whitelist
        actual_season_ids = [s.id for s in result.seasons if s.filtered]
        actual_episode_ids = [e.id for e in result.episodes if e.filtered]
        assert actual_season_ids == (expected_season_ids or [])
        assert actual_episode_ids == (expected_episode_ids or [])
        assert [EpisodeOutput.model_validate(e) for e in result.episodes] == [
            EpisodeOutput.model_validate(episode) for episode in episodes
        ]

    # TODO: Validate
    @pytest.mark.parametrize("plugin_is_public", [True, False])
    @pytest.mark.parametrize("user_owns_plugin", [True, False])
    def test_get_shows_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_owns_plugin: bool,
        plugin_is_public: bool,
    ) -> None:
        """Test show listing with plugin visibility and plugin ownership.

        The channel is public and the user is the channel owner. Shows from
        private plugins should only be visible if the user also owns the plugin.
        """
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )
        plugin_owner = (
            initial_test_data.user
            if user_owns_plugin
            else create_random_user(session_scoped_session)
        )
        plugin = create_random_plugin(
            session_scoped_session,
            plugin_owner,
            visibility=Visibility.public if plugin_is_public else Visibility.private,
        )

        show = create_random_show(session_scoped_session, plugin)
        create_random_episode(session_scoped_session, show)
        create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            show,
        )

        url = f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/shows"
        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=url,
            output_schema=ChannelShowsOutput,
            headers=initial_test_data.headers,
        )
        if plugin_is_public or user_owns_plugin:
            assert len(result.shows) == 1
        else:
            assert len(result.shows) == 0

    # TODO: Validate
    @pytest.mark.parametrize("plugin_is_public", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_get_whitelist_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_owner: bool,
        plugin_is_public: bool,
    ) -> None:
        """Test whitelist endpoint with plugin visibility and channel ownership.

        The whitelist endpoint requires channel ownership AND that the show is
        readable. Non-owners get a channel permission error. Owners with an
        unreadable show (private plugin owned by someone else) get a show
        permission error.
        """
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=True,
            record_is_public=True,
        )
        other_user = create_random_user(session_scoped_session)
        plugin = create_random_plugin(
            session_scoped_session,
            other_user,
            visibility=Visibility.public if plugin_is_public else Visibility.private,
        )
        show = create_random_show(session_scoped_session, plugin)
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            show,
        )
        episode = create_random_episode(session_scoped_session, show)

        url = f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/whitelist/{show.id}"
        if user_is_owner and plugin_is_public:
            self.assert_whitelist_success(
                session_scoped_client,
                initial_test_data.record,
                channel_show,
                show,
                [episode],
                initial_test_data.headers,
            )
        elif not user_is_owner:
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=url,
                detail="Not authorized to access this Channel",
                headers=initial_test_data.headers,
            )
        else:
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=url,
                detail="Not authorized to access this Show",
                headers=initial_test_data.headers,
            )

    # TODO: Validate
    @pytest.mark.parametrize("episode_count", [0, 1, 2])
    def test_read_whitelist(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        episode_count: int,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            initial_test_data.user,
        )
        show = channel_show_show(session_scoped_session, channel_show)
        episodes = [
            create_random_episode(session_scoped_session, show)
            for _ in range(episode_count)
        ]
        self.assert_whitelist_success(
            session_scoped_client,
            initial_test_data.record,
            channel_show,
            show,
            episodes,
            initial_test_data.headers,
        )


# TODO: Validate
@dataclass
class WhitelistUpdateTestData:
    user: User
    user_headers: dict[str, str]
    channel: Channel
    channel_show: ChannelShow
    show: Show
    preserved_marked_episode: Episode
    preserved_unmarked_episode: Episode
    target_episode: Episode
    initial_input: WhitelistShowInput


# TODO: Validate
class TestUpdateWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "patch"
    sub_parameters = WhitelistShowInput(is_whitelist=True).model_dump(mode="json")

    # TODO: Validate
    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # TODO: record_is_public is required by the base signature but unused here.
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

    # TODO: Validate
    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    # TODO: Validate
    @staticmethod
    def assert_whitelist_state(
        result: WhitelistShowOutput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        assert result.is_whitelist is expected_mode
        assert {e.id for e in result.episodes if e.filtered} == expected_episode_ids
        assert {s.id for s in result.seasons if s.filtered} == expected_season_ids

    # TODO: reduce parameter count, e.g. group args into a params/dataclass object.
    # TODO: Validate
    def assert_update_result(  # noqa: PLR0913
        self,
        session_scoped_client: TestClient,
        setup: WhitelistUpdateTestData,
        update_input: WhitelistShowInput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        result = assert_success(
            client=session_scoped_client,
            method="patch",
            url=f"{settings.API_V1_STR}/channels/{setup.channel.id}/whitelist/{setup.show.id}",
            output_schema=WhitelistShowOutput,
            headers=setup.user_headers,
            parameters=update_input.model_dump(mode="json"),
        )
        self.assert_whitelist_state(
            result,
            expected_mode=expected_mode,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )

    # TODO: Validate
    def create_whitelist_test_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> WhitelistUpdateTestData:

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            initial_test_data.user,
            is_whitelist=True,
        )
        show = channel_show_show(session_scoped_session, channel_show)
        episodes = [
            create_random_episode(session_scoped_session, show) for _ in range(3)
        ]
        preserved_marked_episode = episodes[0]
        preserved_unmarked_episode = episodes[1]
        target_episode = episodes[2]

        seasons = [
            WhitelistEntryInput(id=preserved_marked_episode.season.id, marked=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.season.id, marked=False),
        ]
        episodes_input = [
            WhitelistEntryInput(id=preserved_marked_episode.id, marked=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.id, marked=False),
        ]
        seasons.append(WhitelistEntryInput(id=target_episode.season.id, marked=True))
        episodes_input.append(WhitelistEntryInput(id=target_episode.id, marked=True))
        initial_input = WhitelistShowInput(
            is_whitelist=True,
            seasons=seasons,
            episodes=episodes_input,
        )

        return WhitelistUpdateTestData(
            user=initial_test_data.user,
            user_headers=initial_test_data.headers,
            channel=initial_test_data.record,
            channel_show=channel_show,
            show=show,
            preserved_marked_episode=preserved_marked_episode,
            preserved_unmarked_episode=preserved_unmarked_episode,
            target_episode=target_episode,
            initial_input=initial_input,
        )

    # TODO: Validate
    def test_update_whitelist_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = self.create_whitelist_test_data(
            session_scoped_client,
            session_scoped_session,
        )
        update_whitelist(
            session_scoped_session,
            setup.channel_show,
            setup.initial_input,
        )

        update_input = WhitelistShowInput(
            is_whitelist=True,
            seasons=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.season.id,
                    marked=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.season.id, marked=False),
            ],
            episodes=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.id,
                    marked=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.id, marked=False),
            ],
        )
        expected_episode_ids = {
            setup.preserved_marked_episode.id,
            setup.preserved_unmarked_episode.id,
        }
        expected_season_ids = {
            setup.preserved_marked_episode.season.id,
            setup.preserved_unmarked_episode.season.id,
        }
        self.assert_update_result(
            session_scoped_client,
            setup,
            update_input,
            expected_mode=True,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )
