from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.canonical_media.keys import tmdb_show_key
from app.media.media_type import TMDBMediaType
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.media import TMDBMedia, TMDBMovie, TMDBSeries
from plugins.TMDB.shared import (
    MOVIE_URL_REGEX,
    TV_URL_REGEX,
    TMDBShared,
    media_url,
)
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


class TMDBDispatch(BaseImporter, TMDBShared):
    """Dispatches the input the appropriate TMDB media plugin based on the URL."""

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    def _media_plugin(self, show: Show) -> TMDBMedia:
        media_type, _ = get_media_type_and_tmdb_id(show.key)
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self)
        return TMDBSeries(self)

    @override
    def import_url(
        self,
        url: str,
        *,
        known_title: bool = False,
    ) -> list[URLImportResult]:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return TMDBMovie(self).import_url(url)
        if re.match(domain_regex + TV_URL_REGEX, url):
            return TMDBSeries(self).import_url(url)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._media_plugin(show).update_show(show, force=force)

    @override
    def update_season(self, season: Season) -> None:
        self._media_plugin(season.show).update_season(season)

    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_plugin(episode.season.show).update_episode(episode)


class TMDBInitializer(BasePluginInitializer, TMDBShared):
    """Class for initializing TMDB's database entries."""



class TMDB(TMDBShared, AbstractPlugin, register=True):
    initializer = TMDBInitializer
    importer = TMDBDispatch

    def import_search(
        self,
        title: str,
        media_type: TMDBMediaType | None = None,
        year: int | None = None,
    ) -> Show | None:
        """Import the first matching title found via search."""
        search_result = self.first_search_result(title, media_type, year)
        if not search_result:
            return None

        media_type, tmdb_key = search_result
        if media_type == TMDBMediaType.movie:
            return self.import_movie(tmdb_key)
        return self.import_show(tmdb_key)

    def import_show(self, tmdb_id: int) -> Show:
        """Import a TMDB tv entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.tv, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.tv, tmdb_id)).one()

    def import_movie(self, tmdb_id: int) -> Show:
        """Import a TMDB movie entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.movie, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.movie, tmdb_id)).one()
