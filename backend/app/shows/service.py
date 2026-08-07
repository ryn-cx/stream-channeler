# TODO: Validate
"""Show services."""

from typing import Literal

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.watches.services import get_installed_plugin
from plugins.TMDB import TMDB
from plugins.TMDB.mixin import highest_episode_number


def relink_children(session: Session, show: Show) -> None:
    """Repoint every child of a `Show` at the TMDB title it now names.

    The linking functions leave a child that is already linked alone, so each
    child's identifier is reset to the website's own first, which is what lets
    the title's new TMDB id take its place. An `episode_identifier` the `User`
    locked is kept as they set it, and the `Show`'s own identifier is whatever
    the `User` set, so it is never rewritten here.
    """
    tmdb = TMDB(session)
    media_type = _tmdb_media_type(session, show)
    plugin_key = show.source.plugin.key

    if show.tmdb_id:
        tmdb.import_title(media_type, show.tmdb_id)

    for season in show.seasons:
        season.season_identifier = f"{plugin_key} {season.key}"
        tmdb.tmdb_link_season(season, show.tmdb_id, season.season_number, media_type)
        _relink_episodes(tmdb, season, show.tmdb_id, media_type)

    session.commit()


def relink_season_children(session: Session, season: Season) -> None:
    """Repoint every `Episode` of a `Season` at TMDB after its `tmdb_id` changed.

    The linking functions leave an `Episode` that is already linked alone, so
    each one's identifier is reset to the website's own first, which is what lets
    the one TMDB reports take its place. An
    `episode_identifier` the `User` locked is kept as they set it. The
    `Season`'s own identifier is whatever the `User` set, so it is never
    rewritten here.
    """
    show = season.show
    tmdb = TMDB(session)
    media_type = _tmdb_media_type(session, show)

    if show.tmdb_id:
        tmdb.import_title(media_type, show.tmdb_id)

    _relink_episodes(tmdb, season, show.tmdb_id, media_type)

    session.commit()


def _relink_episodes(
    tmdb: TMDB,
    season: Season,
    tmdb_id: int | None,
    media_type: Literal["movie", "tv"],
) -> None:
    last_number = highest_episode_number(
        episode.episode_number
        for episode in season.episodes
        if episode.deleted_at is None
    )
    for episode in season.episodes:
        _relink_episode(tmdb, episode, season, tmdb_id, media_type, last_number)


def _relink_episode(  # noqa: PLR0913 - Passed straight to `tmdb_link_episode`.
    tmdb: TMDB,
    episode: Episode,
    season: Season,
    tmdb_id: int | None,
    media_type: Literal["movie", "tv"],
    last_number: int | None,
) -> None:
    locked_identifier = (
        episode.episode_identifier if episode.episode_identifier_locked else None
    )
    # An episode already linked keeps that link, so it is dropped back to the
    # website's own identifier to let the title's new TMDB id reach it.
    episode.episode_identifier = f"{season.show.source.plugin.key} {episode.key}"
    tmdb.tmdb_link_episode(
        episode,
        tmdb_id,
        season.season_number,
        episode.episode_number,
        media_type,
        last_number,
    )
    if locked_identifier:
        episode.episode_identifier = locked_identifier


def _tmdb_media_type(session: Session, show: Show) -> Literal["movie", "tv"]:
    """Ask the `Show`'s plugin whether TMDB holds it as a film or a series.

    Matched on the method rather than on `TMDBMixin`, because a plugin can hand
    its media off to more than one importer and answer for them itself without
    being one.
    """
    plugin_class = get_installed_plugin(show.source.plugin.key)
    if plugin_class is None or not hasattr(plugin_class, "_tmdb_media_type"):
        return "tv"
    return plugin_class(session)._tmdb_media_type(show.key)  # type: ignore[attr-defined,no-any-return]  # noqa: SLF001
