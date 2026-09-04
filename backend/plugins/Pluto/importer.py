# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Pluto.base import PlutoBase
from plugins.Pluto.constants import DETAILS_REGEX, ITEM_ID_REGEX, LOCALE_REGEX
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin_v2.importer import BaseImporter

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class PlutoImporter(BaseImporter, PlutoBase):
    # https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details
    # https://pluto.tv/us/on-demand/movies/68a54f49df1220b53566f16e
    _MOVIE_URL_REGEX = (
        rf"{LOCALE_REGEX}\/on-demand\/movies\/(?P<movie_key>{ITEM_ID_REGEX})"
        rf"{DETAILS_REGEX}(?:\/|$)"
    )
    # https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1/episode/5ef05c6ecdce3c001a779a95
    _SERIES_URL_REGEX = (
        rf"{LOCALE_REGEX}\/on-demand\/series\/(?P<series_key>{ITEM_ID_REGEX})"
        # The optional segments of a link that points at a season or an
        # episode of a series.
        rf"(?:\/season\/\d+(?:\/episode\/(?P<episode_key>{ITEM_ID_REGEX}))?)?"
        rf"{DETAILS_REGEX}(?:\/|$)"
    )

    _episode_key: str | None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._SERIES_URL_REGEX)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        self._episode_key = None
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            show_key = match.group("movie_key")
            self._media_type = "movie"
            self.raise_if_invalid_file(self.items_file(show_key), url)
            return show_key

        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self._media_type = "series"
            self.raise_if_invalid_file(self.seasons_file(show_key), url)
            self._episode_key = match.group("episode_key")
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]

        msg = f"Episode {self._episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)
