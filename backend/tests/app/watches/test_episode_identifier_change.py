# TODO: Validate
"""What a watch stays attached to when the episode under it moves.

A watch carries the identifier of the link that played it rather than that link's
id, so it goes on counting for the media through a rename, and counts for every
other website carrying the same media.
"""

import pytest
from sqlmodel import Session, select

from app.schemas import ReadOptions
from app.watches.exceptions import WatchAlreadyExistsError
from app.watches.models import Watch
from app.watches.schemas import WatchCreate
from app.watches.services import create_watch, get_watched_episodes
from tests.app.episodes.utils import create_linked_episode, create_random_episode
from tests.app.users.utils import create_random_user
from tests.app.watches.utils import create_random_watch


# TODO: Validate
def test_a_watch_stays_with_its_episode_through_a_rename(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)

    episode.watch_identifier = f"{episode.watch_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    stored = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored.episode_id == episode.id


# TODO: Validate
def test_a_watch_reads_back_under_the_identifier_it_was_made_with(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_linked_episode(function_scoped_session)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)

    output = get_watched_episodes(
        function_scoped_session,
        user,
        ReadOptions.model_validate({"sort_options": "[]", "filter_options": "[]"}),
    )
    assert [item.id for item in output.watches] == [watch.id]


# TODO: Validate
def test_another_episode_does_not_take_over_the_watch(
    function_scoped_session: Session,
) -> None:
    """Taking on the identifier a watch was made under does not take the watch."""
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)
    original_identifier = episode.watch_identifier

    other_episode = create_random_episode(function_scoped_session)
    episode.watch_identifier = f"{original_identifier}-changed"
    other_episode.watch_identifier = original_identifier
    function_scoped_session.add(episode)
    function_scoped_session.add(other_episode)
    function_scoped_session.flush()

    stored = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored.episode_id == episode.id


# TODO: Validate
def test_a_watch_counts_for_every_episode_under_the_same_identifier(
    function_scoped_session: Session,
) -> None:
    """The same media on another website is the same media, watch and all."""
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session)
    create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        verified=False,
    )
    other_source_episode = create_random_episode(
        function_scoped_session,
        watch_identifier=episode.watch_identifier,
    )
    function_scoped_session.flush()

    with pytest.raises(WatchAlreadyExistsError):
        create_watch(
            function_scoped_session,
            user.id,
            other_source_episode,
            WatchCreate(),
        )


# TODO: Validate
def test_deleting_the_episode_leaves_the_watch_behind(
    function_scoped_session: Session,
) -> None:
    """A watch outlives the link it was made against, which is the point of it."""
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)

    function_scoped_session.delete(episode)
    function_scoped_session.flush()
    # The column is cleared by the database, so what the session is holding is
    # stale until it goes back for it.
    function_scoped_session.expire_all()

    stored = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored.episode_id is None
