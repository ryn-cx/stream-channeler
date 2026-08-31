# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.Pluto.base import PlutoBase
from plugins.Pluto.constants import DETAILS_REGEX, ITEM_ID_REGEX, LOCALE_REGEX
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.workers import URLImporter


# TODO: Validate
class PlutoImportURL(URLImporter, PlutoBase):
    # https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details
    # https://pluto.tv/us/on-demand/movies/68a54f49df1220b53566f16e
    _MOVIE_URL_REGEX = (
        rf"{LOCALE_REGEX}\/on-demand\/movies\/(?P<movie_id>{ITEM_ID_REGEX})"
        rf"{DETAILS_REGEX}(?:\/|$)"
    )
    # https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1/episode/5ef05c6ecdce3c001a779a95
    _SERIES_URL_REGEX = (
        rf"{LOCALE_REGEX}\/on-demand\/series\/(?P<series_id>{ITEM_ID_REGEX})"
        # The optional segments of a link that points at a season or an
        # episode of a series.
        rf"(?:\/season\/\d+(?:\/episode\/{ITEM_ID_REGEX})?)?"
        rf"{DETAILS_REGEX}(?:\/|$)"
    )

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._SERIES_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self._media_type = "movie"
            self.raise_if_invalid_file(self.items_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            self._show_key = match.group("series_id")
            self._media_type = "series"
            self.raise_if_invalid_file(self.seasons_file(self._show_key), url)
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
