import uuid
from functools import partial

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel, ChannelShow
from app.channels.schemas import WhitelistShowOutput
from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from tests.channels.router import BaseChannelSubEndpointTests
from tests.channels.utils import create_random_channel, create_random_channel_show
from tests.episodes.utils import create_random_episode
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import (
    assert_not_found,
    assert_success,
)


class TestGetWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "get"
    sub_assert_response = staticmethod(
        partial(
            assert_not_found,
            detail="Show was not found on channel",
        ),
    )

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    def assert_whitelist_success(
        self,
        client: TestClient,
        channel: Channel,
        channel_show: ChannelShow,
        episodes: list[Episode],
        headers: dict[str, str],
        *,
        expected_season_ids: list[uuid.UUID] | None = None,
        expected_episode_ids: list[uuid.UUID] | None = None,
    ) -> None:
        result = assert_success(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/whitelist/{channel_show.show_id}",
            output_model=WhitelistShowOutput,
            headers=headers,
        )
        assert result.whitelist_mode == channel_show.white_list_mode
        assert result.enabled_season_ids == (expected_season_ids or [])
        assert result.enabled_episode_ids == (expected_episode_ids or [])
        assert result.episodes == [
            EpisodeOutput.model_validate(episode) for episode in episodes
        ]

    @pytest.mark.parametrize("episode_count", [0, 1, 2])
    def test_read_whitelist(
        self,
        client: TestClient,
        db: Session,
        episode_count: int,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_random_channel(db, user_id=user.id)
        channel_show = create_random_channel_show(db, channel, user_id=user.id)
        episodes = [
            create_random_episode(db, show=channel_show.show)
            for _ in range(episode_count)
        ]
        self.assert_whitelist_success(
            client,
            channel,
            channel_show,
            episodes,
            user.headers,
        )
