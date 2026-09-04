# TODO: Validate
"""The TMDB plugin, and the two halves of the catalogue it reads a title as."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.canonical_media.keys import tmdb_show_key
from app.media.media_type import TMDBMediaType
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.media import TMDBMovie, TMDBSeries
from plugins.TMDB.shared import MOVIE_URL_REGEX, TV_URL_REGEX, TMDBShared
from plugins.TMDB.urls import media_url
from plugins.TMDB.utils import first_search_result
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class TMDBDispatch(TMDBShared):
    """Sends a title to the half of the catalogue it belongs to.

    Kept apart from `TMDBShared` rather than folded into it because what it hands
    a title to is a `TMDBSeries` or a `TMDBMovie`, and those are built on
    `TMDBShared`. Were these on there too, the half being dispatched to would
    inherit the dispatch and hand the title straight back to itself.
    """

    # TODO: Validate
    def _media_plugin(self, show_key: str) -> TMDBShared:
        media_type, _ = get_media_type_and_tmdb_id(show_key)
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self)
        return TMDBSeries(self)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._media_plugin(show.key).update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._media_plugin(season.show.key).update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_plugin(episode.season.show.key).update_episode(episode)


# TODO: Validate
class TMDBInitializer(BasePluginInitializer, TMDBShared): ...


# TODO: Validate
class TMDBImporter(BaseImporter, TMDBDispatch):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return TMDBMovie(self).import_url(url, canonical_show)

        if re.match(domain_regex + TV_URL_REGEX, url):
            return TMDBSeries(self).import_url(url, canonical_show)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)


# TODO: Validate
class TMDB(TMDBDispatch, AbstractPlugin, register=True):
    initializer = TMDBInitializer
    importer = TMDBImporter

    # TODO: Validate
    def import_search(
        self,
        title: str,
        media_type: TMDBMediaType | None = None,
        year: int | None = None,
    ) -> Show | None:
        """Import the first matching title found via search."""
        search_result = first_search_result(self, title, media_type, year)
        if not search_result:
            return None

        media_type, tmdb_key = search_result
        if media_type == TMDBMediaType.movie:
            return self.import_movie(tmdb_key)
        return self.import_show(tmdb_key)

    # TODO: Validate
    def import_show(self, tmdb_id: int) -> Show:
        """Import a TMDB tv entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.tv, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.tv, tmdb_id)).one()

    # TODO: Validate
    def import_movie(self, tmdb_id: int) -> Show:
        """Import a TMDB movie entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.movie, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.movie, tmdb_id)).one()
