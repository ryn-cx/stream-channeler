# TODO: This is completely AI generated.
from sqlmodel import Session, select

from app.schemas import ReadOptions
from app.watches.models import Watch
from app.watches.schemas import WatchCreate
from app.watches.services import create_watches, get_watched_episodes
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import create_random_user
from tests.app.watches.utils import create_random_watch


def test_watch_row_survives_identifier_change(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        episode_identifier=episode.episode_identifier,
    )
    original_identifier = episode.episode_identifier

    episode.episode_identifier = f"{original_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    stored_watch = function_scoped_session.exec(
        select(Watch).where(Watch.id == watch.id),
    ).one()
    assert stored_watch.episode_identifier == original_identifier


def test_watch_is_hidden_after_identifier_change(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        episode_identifier=episode.episode_identifier,
    )

    before = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert [item.id for item in before.watches] == [watch.id]

    episode.episode_identifier = f"{episode.episode_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    after = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert after.watches == []
    assert after.episodes == {}


def test_episode_is_watchable_again_after_identifier_change(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        episode_identifier=episode.episode_identifier,
        verified=False,
    )

    episode.episode_identifier = f"{episode.episode_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    created = create_watches(
        function_scoped_session,
        user.id,
        episode,
        WatchCreate(),
    )
    assert created[0].episode_identifier == episode.episode_identifier

    watches = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert [item.id for item in watches.watches] == [created[0].id]


def test_watch_reattaches_when_identifier_is_restored(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        episode_identifier=episode.episode_identifier,
    )
    original_identifier = episode.episode_identifier

    episode.episode_identifier = f"{original_identifier}-changed"
    function_scoped_session.add(episode)
    function_scoped_session.flush()
    assert (
        get_watched_episodes(
            function_scoped_session,
            user,
            ReadOptions(),
        ).watches
        == []
    )

    episode.episode_identifier = original_identifier
    function_scoped_session.add(episode)
    function_scoped_session.flush()

    restored = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert [item.id for item in restored.watches] == [watch.id]


def test_watch_follows_identifier_onto_a_different_episode(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episode = create_random_episode(function_scoped_session, user)
    watch = create_random_watch(
        function_scoped_session,
        episode,
        watch_user=user,
        episode_identifier=episode.episode_identifier,
    )
    original_identifier = episode.episode_identifier

    other_episode = create_random_episode(function_scoped_session, user)
    episode.episode_identifier = f"{original_identifier}-changed"
    other_episode.episode_identifier = original_identifier
    function_scoped_session.add(episode)
    function_scoped_session.add(other_episode)
    function_scoped_session.flush()

    output = get_watched_episodes(function_scoped_session, user, ReadOptions())
    assert [item.id for item in output.watches] == [watch.id]
    watched_episode_ids = {
        episode_output.id for episode_output in output.episodes.values()
    }
    assert watched_episode_ids == {other_episode.id}


def _episode_identifiers(session: Session, user_id: object) -> set[str]:
    return {
        watch.episode_identifier
        for watch in session.exec(
            select(Watch).where(Watch.user_id == user_id),
        ).all()
    }


def test_identifier_change_does_not_rewrite_watches(
    function_scoped_session: Session,
) -> None:
    user = create_random_user(function_scoped_session)
    episodes = [create_random_episode(function_scoped_session, user) for _ in range(3)]
    for episode in episodes:
        create_random_watch(
            function_scoped_session,
            episode,
            watch_user=user,
            episode_identifier=episode.episode_identifier,
        )
    original_identifiers = {episode.episode_identifier for episode in episodes}

    for index, episode in enumerate(episodes):
        episode.episode_identifier = f"rekeyed-{index}"
        function_scoped_session.add(episode)
    function_scoped_session.flush()

    assert _episode_identifiers(function_scoped_session, user.id) == (
        original_identifiers
    )
    assert (
        get_watched_episodes(
            function_scoped_session,
            user,
            ReadOptions(),
        ).watches
        == []
    )
