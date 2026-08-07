# TODO: Validate
"""Show services."""

from typing import Literal

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.watches.services import get_installed_plugin
from plugins.TMDB import TMDB


def relink_children(
    session: Session,
    show: Show,
    *,
    relink_identifier: bool = True,
) -> None:
    """Repoint every child of a `Show` at TMDB after its `tmdb_id` changed.

    The linking functions leave an existing `tmdb_id` alone, so the one on each
    child is cleared first to let the one from the new `Show` `tmdb_id` take its
    place. An `episode_identifier` the `User` locked is kept as they set it, and
    `relink_identifier` is false when the `User` set the `show_identifier`
    themselves rather than leaving it to follow TMDB.
    """
    tmdb = TMDB(session)
    media_type = _tmdb_media_type(session, show)
    plugin_key = show.source.plugin.key

    if show.tmdb_id:
        tmdb.import_title(media_type, show.tmdb_id)

    if relink_identifier:
        show.show_identifier = (
            f"TMDB {media_type} {show.tmdb_id}"
            if show.tmdb_id
            else f"{plugin_key} {show.key}"
        )

    for season in show.seasons:
        season.tmdb_id = None
        season.season_identifier = f"{plugin_key} {season.key}"
        tmdb.tmdb_link_season(season, show.tmdb_id, season.season_number, media_type)
        _relink_episodes(tmdb, season, show.tmdb_id, media_type)

    session.commit()


def relink_season_children(
    session: Session,
    season: Season,
    *,
    relink_identifier: bool = True,
) -> None:
    """Repoint every `Episode` of a `Season` at TMDB after its `tmdb_id` changed.

    The linking functions leave an existing `tmdb_id` alone, so the one on each
    `Episode` is cleared first to let the one TMDB reports take its place. An
    `episode_identifier` the `User` locked is kept as they set it, and
    `relink_identifier` is false when the `User` set the `season_identifier`
    themselves rather than leaving it to follow TMDB.
    """
    show = season.show
    tmdb = TMDB(session)
    media_type = _tmdb_media_type(session, show)

    if show.tmdb_id:
        tmdb.import_title(media_type, show.tmdb_id)

    if relink_identifier:
        season.season_identifier = (
            f"TMDB {media_type} {season.tmdb_id}"
            if season.tmdb_id
            else f"{show.source.plugin.key} {season.key}"
        )

    _relink_episodes(tmdb, season, show.tmdb_id, media_type)

    session.commit()


def _relink_episodes(
    tmdb: TMDB,
    season: Season,
    tmdb_id: int | None,
    media_type: Literal["movie", "tv"],
) -> None:
    for episode in season.episodes:
        _relink_episode(tmdb, episode, season, tmdb_id, media_type)


def _relink_episode(
    tmdb: TMDB,
    episode: Episode,
    season: Season,
    tmdb_id: int | None,
    media_type: Literal["movie", "tv"],
) -> None:
    locked_identifier = (
        episode.episode_identifier if episode.episode_identifier_locked else None
    )
    episode.tmdb_id = None
    tmdb.tmdb_link_episode(
        episode,
        tmdb_id,
        season.season_number,
        episode.episode_number,
        media_type,
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
