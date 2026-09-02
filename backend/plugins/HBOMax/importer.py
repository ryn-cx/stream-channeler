# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HBOMax.base import HBOMaxBase
from plugins.HBOMax.constants import SLUG_REGEX, UUID_REGEX
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import BaseImporter, record_show

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class HBOMaxImporter(BaseImporter, HBOMaxBase):
    # The title slug HBO Max puts in front of the id is decorative, such as in
    # https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
    _MOVIE_URL_REGEX = rf"\/movies?\/{SLUG_REGEX}(?P<movie_id>{UUID_REGEX})"
    # Any non-movie media-type prefix maps to a series, such as mini-series in
    # https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
    # or shows in
    # https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    # The media-type path segment is any of them, e.g. show, shows, mini-series,
    # limited-series.
    _SHOW_URL_REGEX = rf"\/[a-z-]+\/{SLUG_REGEX}(?:s\d+\/)?(?P<show_id>{UUID_REGEX})"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            show_key = match.group("movie_id")
            self._media_type = "movie"
            self.raise_if_invalid_file(self.movie_file(show_key), url)
            return show_key

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            show_key = match.group("show_id")
            self._media_type = "series"
            self.raise_if_invalid_file(self.show_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._set_media_type_from_show(show)
        super().update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._set_media_type_from_show(season.show)
        super().update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._set_media_type_from_show(episode.season.show)
        super().update_episode(episode)

    # TODO: Validate
    @override
    def on_failure(self, record: Show | Season | Episode, error: Exception) -> None:
        self._set_media_type_from_show(record_show(record))
        super().on_failure(record, error)
