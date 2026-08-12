# TODO: Validate
from typing import Any
from unittest.mock import patch

from sqlmodel import Session

from app.episodes.models import Episode
from app.shows.service import relink_season_children
from tests.old_mess.app.episodes.utils import create_random_episode
from tests.old_mess.app.seasons.utils import create_random_season


# TODO: Validate
def test_relink_season_children_links_every_episode(
    session_scoped_session: Session,
) -> None:
    """Ensure every `Episode` is repointed at TMDB with a cleared `tmdb_id`."""
    season = create_random_season(session_scoped_session, tmdb_id=100)
    episode = create_random_episode(
        session_scoped_session,
        season,
        tmdb_id=200,
        episode_identifier_locked=False,
    )

    with patch("app.shows.service.TMDB") as tmdb_class:
        relink_season_children(session_scoped_session, season)

    tmdb_class.return_value.tmdb_link_episode.assert_called_once_with(
        episode,
        season.show.tmdb_id,
        season.season_number,
        episode.episode_number,
        "tv",
        episode.episode_number,
    )
    assert episode.tmdb_id is None


# TODO: Validate
def test_relink_season_children_keeps_locked_episode_identifier(
    session_scoped_session: Session,
) -> None:
    """Ensure an `episode_identifier` the `User` locked survives the relink."""
    season = create_random_season(session_scoped_session, tmdb_id=100)
    episode = create_random_episode(
        session_scoped_session,
        season,
        episode_identifier="Locked",
        episode_identifier_locked=True,
    )

    # TODO: Validate
    def link(linked_episode: Episode, *_args: Any) -> None:  # noqa: ANN401
        linked_episode.episode_identifier = "TMDB 200"

    with patch("app.shows.service.TMDB") as tmdb_class:
        tmdb_class.return_value.tmdb_link_episode.side_effect = link
        relink_season_children(session_scoped_session, season)

    assert episode.episode_identifier == "Locked"


# TODO: Validate
def test_relink_season_children_replaces_unlocked_episode_identifier(
    session_scoped_session: Session,
) -> None:
    """Ensure an unlocked `episode_identifier` follows the new `tmdb_id`."""
    season = create_random_season(session_scoped_session, tmdb_id=100)
    episode = create_random_episode(
        session_scoped_session,
        season,
        episode_identifier="Locked",
        episode_identifier_locked=False,
    )

    # TODO: Validate
    def link(linked_episode: Episode, *_args: Any) -> None:  # noqa: ANN401
        linked_episode.episode_identifier = "TMDB 200"

    with patch("app.shows.service.TMDB") as tmdb_class:
        tmdb_class.return_value.tmdb_link_episode.side_effect = link
        relink_season_children(session_scoped_session, season)

    assert episode.episode_identifier == "TMDB 200"
