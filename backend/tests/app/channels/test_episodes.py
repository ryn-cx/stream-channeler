# TODO: Validate
"""What a channel's episode read comes back with.

The episodes themselves are chosen by `EpisodeQueryBuilder`, which is tested in
`test_episode_sorting`. What is here is the rest of the answer: the seasons,
shows, sources and plugins each episode is served alongside, so the caller never
has to ask after them one by one.
"""

from sqlmodel import Session

from app.channels import service
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.users.models import User
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import create_random_user


# TODO: Validate
def channel_with_episodes(
    session: Session,
    owner: User,
    show_count: int = 2,
) -> Channel:
    """Build a channel carrying one episode of each of `show_count` shows."""
    channel = create_random_channel(session, user=owner.id)
    for _ in range(show_count):
        channel_show = create_random_channel_show(
            session,
            channel,
            is_whitelist=False,
        )
        create_random_episode(
            session,
            channel_show_show(session, channel_show),
        )
    session.flush()
    return channel


# TODO: Validate
def test_a_channel_with_no_shows_reads_as_empty(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)

    output = service.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    assert output.episodes == []
    assert output.seasons == {}
    assert output.shows == {}
    assert output.sources == {}


# TODO: Validate
def test_every_episode_on_the_channel_is_read(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner)

    output = service.channel_episodes_output(
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
    """The season, show, source and plugin above an episode come back with it."""
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner, show_count=1)

    output = service.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )

    episode = output.episodes[0]
    season = output.seasons[episode.season_id]
    show = output.shows[season.show_id]
    source = output.sources[show.source_id]
    assert source.plugin_id in output.plugins


# TODO: Validate
def test_an_episode_says_which_channel_it_came_from(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner, show_count=1)

    output = service.channel_episodes_output(
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
    """Who is asking changes what is watched, not which episodes are on offer."""
    owner = create_random_user(session_scoped_session)
    channel = channel_with_episodes(session_scoped_session, owner)

    as_owner = service.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        owner,
        session_scoped_session,
    )
    as_visitor = service.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1),
        None,
        session_scoped_session,
    )

    assert {episode.id for episode in as_owner.episodes} == {
        episode.id for episode in as_visitor.episodes
    }
