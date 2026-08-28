# TODO: Validate
"""Tests for reading a channel that combines other channels.

Covers which channel an episode reads as coming from.
"""

import json
import uuid

import pytest
from sqlmodel import Session, col, delete

from app.channels import service
from app.channels.channel_scope import channel_attribution
from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel, ChannelCombinedChannel
from app.channels.schemas import ChannelOptions, CombinedChannelInput
from app.episodes.models import Episode
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
from tests.app.users.utils import create_random_user


# TODO: Validate
@pytest.fixture
def user(session_scoped_session: Session) -> User:
    return create_random_user(session_scoped_session)


# TODO: Validate
@pytest.fixture
def plugin(session_scoped_session: Session) -> Plugin:
    return create_random_plugin(session_scoped_session)


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
def test_saving_and_reading_back_a_channels_combined_channels(
    session_scoped_session: Session,
) -> None:
    session = session_scoped_session
    owner = create_random_user(session)
    channel = create_random_channel(session, user=owner.id, is_public=True)
    first = create_random_channel(session, user=owner.id, is_public=True)
    second = create_random_channel(session, user=owner.id, is_public=True)

    service.replace_combined_channels(
        session,
        owner,
        channel,
        [CombinedChannelInput(id=first.id), CombinedChannelInput(id=second.id)],
    )

    read_back = service.combined_channels_output(channel, session)
    assert {entry.id for entry in read_back} == {first.id, second.id}


# TODO: Validate
def test_a_channel_the_user_cannot_read_is_left_out(
    session_scoped_session: Session,
) -> None:
    """A channel somebody cannot see is not one they can combine into theirs."""
    session = session_scoped_session
    owner = create_random_user(session)
    channel = create_random_channel(session, user=owner.id, is_public=True)
    readable = create_random_channel(session, user=owner.id, is_public=True)
    unreadable = create_random_channel(session, is_public=False)

    service.replace_combined_channels(
        session,
        owner,
        channel,
        [
            CombinedChannelInput(id=readable.id),
            CombinedChannelInput(id=unreadable.id),
        ],
    )

    read_back = service.combined_channels_output(channel, session)
    assert {entry.id for entry in read_back} == {readable.id}


# TODO: Validate
def test_channel_reads_as_itself(
    session_scoped_session: Session,
    user: User,
) -> None:
    channel = create_random_channel(session_scoped_session, user=user.id)
    assert channel_attribution(session_scoped_session, user, channel) == {
        channel.id: channel.id,
    }


# TODO: Validate
def test_grandchild_reads_as_the_channel_it_was_added_through(
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
def test_episodes_group_by_the_channel_they_were_added_through(
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
def test_sorting_by_channel_is_offered() -> None:
    labels = {
        option.label
        for option in service.get_sort_options()
        if option.model == "channel"
    }
    assert labels == {"Channel - Id"}
