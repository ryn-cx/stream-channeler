# TODO: Validate

from sqlmodel import Session

from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.channels.service import episodes
from app.users.models import User
from tests.app.channels.utils import (
    channel_title_title,
    create_random_channel,
    create_random_channel_title,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import create_random_user


# TODO: Validate
def channel_with_episodes(
    session: Session,
    owner: User,
    title_count: int = 2,
) -> Channel:
    """Build a channel carrying one episode of each of `title_count` titles."""
    channel = create_random_channel(session, user=owner.id)
    for _ in range(title_count):
        channel_title = create_random_channel_title(
            session,
            channel,
            is_whitelist=False,
        )
        create_random_episode(
            session,
            channel_title_title(session, channel_title),
        )
    session.flush()
    return channel


# TODO: Validate
def test_a_channel_with_no_titles_reads_as_empty(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)

    output = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    assert output.episodes == []
    assert output.seasons == {}
    assert output.titles == {}
    assert output.sources == {}


# TODO: Validate
def test_every_episode_on_the_channel_is_read(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner)

    output = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    assert len(output.episodes) == 2  # noqa: PLR2004 - The number is the point of the test.


# TODO: Validate
def test_an_episode_is_served_with_what_it_hangs_off(
    session_scoped_session: Session,
) -> None:
    """The season, title, source and plugin above an episode come back with it."""
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner, title_count=1)

    output = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    episode = output.episodes[0]
    season = output.seasons[episode.season_id]
    title = output.titles[season.title_id]
    source = output.sources[title.source_id]
    assert source.plugin_id in output.plugins


# TODO: Validate
def test_an_episode_says_which_channel_it_came_from(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner, title_count=1)

    output = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    assert output.episodes[0].channel_id == channel.id
    assert output.episodes[0].channel_ids == [channel.id]
    assert channel.id in output.channels


# TODO: Validate
def test_a_channel_reads_the_same_for_a_visitor(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner)

    as_owner = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )
    as_visitor = episodes.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        None,
        session_scoped_session,
    )

    assert {episode.id for episode in as_owner.episodes} == {
        episode.id for episode in as_visitor.episodes
    }
