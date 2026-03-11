# TODO: Validate
import uuid
from dataclasses import dataclass
from functools import partial

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel, ChannelShow
from app.channels.schemas import (
    WhitelistEntryInput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.channels.service import update_whitelist
from app.config import settings
from app.episodes.models import Episode
from tests.channels.router import BaseChannelSubEndpointTests
from tests.channels.utils import create_random_channel, create_random_channel_show
from tests.episodes.utils import create_random_episode
from tests.users.utils import CreatedUser, create_random_user_alt
from tests.utils.route_assertions import (
    assert_not_found,
    assert_success,
)


@dataclass
class WhitelistUpdateTestData:
    user: CreatedUser
    channel: Channel
    channel_show: ChannelShow
    preserved_marked_episode: Episode
    preserved_unmarked_episode: Episode
    target_episode: Episode
    initial_input: WhitelistShowInput


class TestUpdateWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "patch"
    sub_assert_response = staticmethod(
        partial(
            assert_not_found,
            detail="Show was not found on channel",
        ),
    )
    sub_parameters = WhitelistShowInput(whitelist_mode=True).model_dump(mode="json")

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    @staticmethod
    def assert_whitelist_state(
        result: WhitelistShowOutput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        assert result.whitelist_mode is expected_mode
        assert set(result.enabled_episode_ids) == expected_episode_ids
        assert set(result.enabled_season_ids) == expected_season_ids

    def assert_update_result(
        self,
        client: TestClient,
        setup: WhitelistUpdateTestData,
        update_input: WhitelistShowInput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        result = assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/channels/{setup.channel.id}/whitelist/{setup.channel_show.show_id}",
            output_model=WhitelistShowOutput,
            headers=setup.user.headers,
            parameters=update_input.model_dump(mode="json"),
        )
        self.assert_whitelist_state(
            result,
            expected_mode=expected_mode,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )

    def create_whitelist_test_data(
        self,
        client: TestClient,
        db: Session,
    ) -> WhitelistUpdateTestData:

        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        channel_show = create_random_channel_show(
            db,
            channel,
            user_id=user.id,
            white_list_mode=True,
        )
        episodes = [create_random_episode(db, show=channel_show.show) for _ in range(3)]
        preserved_marked_episode = episodes[0]
        preserved_unmarked_episode = episodes[1]
        target_episode = episodes[2]

        seasons = [
            WhitelistEntryInput(id=preserved_marked_episode.season.id, enabled=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.season.id, enabled=False),
        ]
        episodes_input = [
            WhitelistEntryInput(id=preserved_marked_episode.id, enabled=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.id, enabled=False),
        ]
        seasons.append(WhitelistEntryInput(id=target_episode.season.id, enabled=True))
        episodes_input.append(WhitelistEntryInput(id=target_episode.id, enabled=True))
        initial_input = WhitelistShowInput(
            whitelist_mode=True,
            seasons=seasons,
            episodes=episodes_input,
        )

        return WhitelistUpdateTestData(
            user=user,
            channel=channel,
            channel_show=channel_show,
            preserved_marked_episode=preserved_marked_episode,
            preserved_unmarked_episode=preserved_unmarked_episode,
            target_episode=target_episode,
            initial_input=initial_input,
        )

    def test_update_whitelist_data(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        setup = self.create_whitelist_test_data(
            client,
            db,
        )
        update_whitelist(db, setup.channel_show, setup.initial_input)

        update_input = WhitelistShowInput(
            whitelist_mode=True,
            seasons=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.season.id,
                    enabled=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.season.id, enabled=False),
            ],
            episodes=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.id,
                    enabled=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.id, enabled=False),
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
            client,
            setup,
            update_input,
            expected_mode=True,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )
