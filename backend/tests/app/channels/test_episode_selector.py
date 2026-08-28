# TODO: Validate
"""How a watch changes what a channel offers.

An episode is unwatched, started, or finished, and the three filters between them
say which of those a `User` wants to see. A started watch is one that was
recorded but never verified; a finished one has been verified.
"""

import pytest
from sqlmodel import Session

from app.channels import service
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.users.models import User
from app.watches.models import Watch
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import create_random_user
from tests.app.watches.utils import create_random_watch


# TODO: Validate
@pytest.fixture
def owner(session_scoped_session: Session) -> User:
    return create_random_user(session_scoped_session)


# TODO: Validate
@pytest.fixture
def channel(session_scoped_session: Session, owner: User) -> Channel:
    """Build a channel holding one episode, which each test watches or does not."""
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(
        session_scoped_session,
        channel,
        is_whitelist=False,
    )
    create_random_episode(
        session_scoped_session,
        channel_show_show(session_scoped_session, channel_show),
    )
    session_scoped_session.flush()
    return channel


# TODO: Validate
def episodes(
    session: Session,
    channel: Channel,
    owner: User,
    **options: bool,
) -> list[object]:
    output = service.channel_episodes_output(
        channel,
        ChannelOptions(random_seed=1, **options),
        owner,
        session,
    )
    return output.episodes


# TODO: Validate
def watch(session: Session, channel: Channel, owner: User, *, verified: bool) -> Watch:
    """Record the owner having watched the channel's one episode."""
    show = channel_show_show(session, channel.shows[0])
    return create_random_watch(
        session,
        show.seasons[0].episodes[0],
        watch_user=owner,
        verified=verified,
    )


# TODO: Validate
def test_an_unwatched_episode_is_offered(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    assert len(episodes(session_scoped_session, channel, owner)) == 1


# TODO: Validate
def test_a_started_watch_comes_back_with_the_episode(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    started = watch(session_scoped_session, channel, owner, verified=False)

    offered = episodes(session_scoped_session, channel, owner)

    assert [episode.episode_watch_id for episode in offered] == [started.id]
    assert [episode.verified for episode in offered] == [False]


# TODO: Validate
def test_hiding_partially_watched_hides_a_started_watch(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    watch(session_scoped_session, channel, owner, verified=False)

    assert (
        episodes(
            session_scoped_session,
            channel,
            owner,
            hide_partially_watched=True,
        )
        == []
    )


# TODO: Validate
def test_hiding_partially_watched_keeps_a_finished_watch(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    finished = watch(session_scoped_session, channel, owner, verified=True)

    offered = episodes(
        session_scoped_session,
        channel,
        owner,
        hide_partially_watched=True,
    )

    assert [episode.episode_watch_id for episode in offered] == [finished.id]


# TODO: Validate
def test_hiding_watched_hides_a_finished_watch(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    watch(session_scoped_session, channel, owner, verified=True)

    assert episodes(session_scoped_session, channel, owner, hide_watched=True) == []


# TODO: Validate
def test_hiding_watched_keeps_a_started_watch(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    """A watch that was never finished is not something the `User` has watched."""
    started = watch(session_scoped_session, channel, owner, verified=False)

    offered = episodes(session_scoped_session, channel, owner, hide_watched=True)

    assert [episode.episode_watch_id for episode in offered] == [started.id]


# TODO: Validate
def test_asking_for_started_episodes_only(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    """Hiding both the watched and the unwatched leaves what was started."""
    started = watch(session_scoped_session, channel, owner, verified=False)

    offered = episodes(
        session_scoped_session,
        channel,
        owner,
        hide_watched=True,
        hide_unwatched=True,
    )

    assert [episode.episode_watch_id for episode in offered] == [started.id]


# TODO: Validate
def test_asking_for_started_episodes_hides_a_finished_watch(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    watch(session_scoped_session, channel, owner, verified=True)

    assert (
        episodes(
            session_scoped_session,
            channel,
            owner,
            hide_watched=True,
            hide_unwatched=True,
        )
        == []
    )


# TODO: Validate
def test_asking_for_started_episodes_hides_an_unwatched_one(
    session_scoped_session: Session,
    channel: Channel,
    owner: User,
) -> None:
    assert (
        episodes(
            session_scoped_session,
            channel,
            owner,
            hide_watched=True,
            hide_unwatched=True,
        )
        == []
    )
