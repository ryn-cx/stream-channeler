# TODO: Validate
# TODO: This is completely AI generated.
import pytest
from sqlmodel import Session, select

from app.schemas import ReadOptions
from app.watches.exceptions import WatchAlreadyExistsError
from app.watches.models import Watch
from app.watches.schemas import WatchCreate
from app.watches.services import create_watch, get_watched_episodes
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import create_random_user
from tests.app.watches.utils import create_random_watch


# TODO: Validate
def test_watch_follows_episode_through_identifier_change(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)

    episode.episode_identifier = f"{episode.episode_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    stored_watch = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored_watch.episode_id == episode.id

    output = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert [item.id for item in output.watches] == [watch.id]
    assert [item.episode_identifier for item in output.watches] == [
        episode.episode_identifier,
    ]


# TODO: Validate
def test_watch_is_not_taken_over_by_another_episode(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)
    original_identifier = episode.episode_identifier

    other_episode = create_random_episode(function_scoped_session, user)
    episode.episode_identifier = f"{original_identifier}-changed"
    other_episode.episode_identifier = original_identifier
    function_scoped_session.add(episode)
    function_scoped_session.add(other_episode)
    function_scoped_session.flush()

    stored_watch = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored_watch.episode_id == episode.id


# TODO: Validate
def test_watch_counts_for_every_episode_sharing_an_identifier(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        verified=False,
    )
    other_source_episode = create_random_episode(
        function_scoped_session,
        user,
        episode_identifier=episode.episode_identifier,
    )
    function_scoped_session.flush()

    # The same media from another source shares the identifier, so the existing
    # unverified watch still counts for it.
    with pytest.raises(WatchAlreadyExistsError):
        create_watch(
            function_scoped_session,
            user.id,
            other_source_episode,
            WatchCreate(),
        )


# TODO: Validate
def test_deleting_the_episode_removes_its_watches(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(function_scoped_session, episode, watch_user=user)

    function_scoped_session.delete(episode)
    function_scoped_session.flush()

    assert (
        function_scoped_session.exec(
            select(Watch).where(Watch.id == watch.id),
        ).one_or_none()
        is None
    )
