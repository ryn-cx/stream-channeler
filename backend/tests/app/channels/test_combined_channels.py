# TODO: Validate
"""Tests for reading a channel that combines other channels.

Covers which channel an episode reads as coming from.
"""

import json
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete

from app.channels.channel_scope import channel_attribution
from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel, ChannelCombinedChannel
from app.channels.schemas import ChannelOptions
from app.config import settings
from app.episodes.models import Episode
from app.models import Visibility
from app.plugins.models import Plugin
from app.users.models import User
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.plugins.utils import create_random_plugin
from tests.app.seasons.utils import create_random_season
from tests.app.users.utils import authentication_token_from_email, create_random_user


# TODO: Validate
@pytest.fixture
def user(session_scoped_session: Session) -> User:
    return create_random_user(session_scoped_session)


# TODO: Validate
@pytest.fixture
def plugin(session_scoped_session: Session, user: User) -> Plugin:
    return create_random_plugin(
        session_scoped_session,
        user,
        visibility=Visibility.public,
    )


# TODO: Validate
def _combine(
    session: Session,
    channel: Channel,
    combined: list[Channel],
) -> None:
    """Replace `channel`'s combined channels."""
    session.exec(  # type: ignore[call-overload]
        delete(ChannelCombinedChannel).where(
            col(ChannelCombinedChannel.channel_id) == channel.id,
        ),
    )
    for combined_channel in combined:
        session.add(
            ChannelCombinedChannel(
                channel_id=channel.id,
                combined_channel_id=combined_channel.id,
            ),
        )
    session.flush()
    session.refresh(channel)


# TODO: Validate
def _channel_with_episodes(
    session: Session,
    user: User,
    plugin: Plugin,
    durations: list[int],
    channel_id: uuid.UUID | None = None,
) -> tuple[Channel, list[Episode]]:
    """Build a channel holding one show whose episodes run for `durations`."""
    channel = (
        create_random_channel(session, user=user.id, id=channel_id)
        if channel_id is not None
        else create_random_channel(session, user=user.id)
    )
    channel_show = create_random_channel_show(
        session,
        channel,
        plugin,
        is_whitelist=False,
    )
    season = create_random_season(session, channel_show_show(session, channel_show))
    episodes = [
        create_random_episode(session, season, duration=duration)
        for duration in durations
    ]
    session.flush()
    return channel, episodes


# TODO: Validate
class TestCombinedChannelsEndpoint:
    # TODO: Validate
    @staticmethod
    def url(channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/combined-channels"

    # TODO: Validate
    def test_saving_and_reading_back_a_channel_s_combined_channels(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        session = session_scoped_session
        user = create_random_user(session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session,
        )
        channel = create_random_channel(session, user=user.id, is_public=True)
        first = create_random_channel(session, user=user.id, is_public=True)
        second = create_random_channel(session, user=user.id, is_public=True)
        session.commit()

        response = session_scoped_client.put(
            self.url(channel.id),
            json=[{"id": str(first.id)}, {"id": str(second.id)}],
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK

        read_back = session_scoped_client.get(self.url(channel.id), headers=headers)
        assert read_back.status_code == status.HTTP_200_OK
        assert {entry["id"] for entry in read_back.json()} == {
            str(first.id),
            str(second.id),
        }


# TODO: Validate
class TestChannelAttribution:
    # TODO: Validate
    def test_channel_reads_as_itself(
        self,
        session_scoped_session: Session,
        user: User,
    ) -> None:
        channel = create_random_channel(session_scoped_session, user=user.id)
        assert channel_attribution(session_scoped_session, user, channel) == {
            channel.id: channel.id,
        }

    # TODO: Validate
    def test_grandchild_reads_as_the_channel_it_was_added_through(
        self,
        session_scoped_session: Session,
        user: User,
    ) -> None:
        session = session_scoped_session
        channel_a = create_random_channel(session, user=user.id)
        channel_b = create_random_channel(session, user=user.id)
        channel_c = create_random_channel(session, user=user.id)
        channel_d = create_random_channel(session, user=user.id)
        _combine(session, channel_c, [channel_d])
        _combine(session, channel_b, [channel_c])
        _combine(session, channel_a, [channel_b])

        attribution = channel_attribution(session, user, channel_a)

        assert attribution[channel_a.id] == channel_a.id
        assert attribution[channel_b.id] == channel_b.id
        # The channels below B were added through B rather than through A.
        assert attribution[channel_c.id] == channel_b.id
        assert attribution[channel_d.id] == channel_b.id

    # TODO: Validate
    def test_a_channel_reached_twice_belongs_to_the_first_that_reaches_it(
        self,
        session_scoped_session: Session,
        user: User,
    ) -> None:
        session = session_scoped_session
        shared = create_random_channel(session, user=user.id)
        first = create_random_channel(session, user=user.id)
        second = create_random_channel(session, user=user.id)
        _combine(session, first, [shared])
        _combine(session, second, [shared])
        parent = create_random_channel(session, user=user.id)
        _combine(session, parent, [first, second])

        attribution = channel_attribution(session, user, parent)

        assert attribution[shared.id] == first.id


# TODO: Validate
class TestSortByChannel:
    # TODO: Validate
    def test_episodes_group_by_the_channel_they_were_added_through(
        self,
        session_scoped_session: Session,
        user: User,
        plugin: Plugin,
    ) -> None:
        session = session_scoped_session
        # The ids are pinned so the order they sort in is known: reading the channel
        # an episode is held by rather than the one it was added through would put
        # C's episodes last instead of alongside B's.
        channel_a, episodes_a = _channel_with_episodes(
            session,
            user,
            plugin,
            [70, 80],
            uuid.UUID(int=1),
        )
        channel_b, episodes_b = _channel_with_episodes(
            session,
            user,
            plugin,
            [10, 20],
            uuid.UUID(int=2),
        )
        channel_d, episodes_d = _channel_with_episodes(
            session,
            user,
            plugin,
            [50, 60],
            uuid.UUID(int=3),
        )
        channel_c, episodes_c = _channel_with_episodes(
            session,
            user,
            plugin,
            [30, 40],
            uuid.UUID(int=4),
        )
        # C is combined into B, so its episodes read as B's rather than as their own.
        _combine(session, channel_b, [channel_c])
        _combine(session, channel_a, [channel_b, channel_d])

        builder = EpisodeQueryBuilder(
            session,
            channel_a,
            ChannelOptions(
                sort_by=[
                    json.dumps(
                        {
                            "model": "channel",
                            "field": "id",
                            "direction": "ascending",
                            "order": "sequential",
                        },
                    ),
                ],
            ),
            user,
        )
        results = builder.get_episodes()
        assert len(results) == 8  # noqa: PLR2004

        position = {result.episode.id: index for index, result in enumerate(results)}

        # TODO: Validate
        def occupies_one_run(episodes: list[Episode]) -> bool:
            """Whether `episodes` were read together rather than scattered."""
            positions = [position[episode.id] for episode in episodes]
            return max(positions) - min(positions) + 1 == len(positions)

        # C was added through B, so its episodes are read as part of B's rather
        # than as a group of their own.
        assert occupies_one_run([*episodes_b, *episodes_c])
        assert occupies_one_run(episodes_a)
        assert occupies_one_run(episodes_d)

    # TODO: Validate
    def test_sorting_by_channel_is_offered(self) -> None:
        from app.channels.service import get_sort_options

        labels = {
            option.label for option in get_sort_options() if option.model == "channel"
        }
        assert labels == {"Channel - Id"}
