# TODO: Validate
"""What the plugin, its importers and its initializer all read HBO Max by."""

from __future__ import annotations

from typing import override

from plugins.HBOMax.basic_files import BasicFiles
from plugins.HBOMax.constants import SLUG_REGEX, UUID_REGEX
from plugins.HBOMax.utils import search_url

# The title slug HBO Max puts in front of the id is decorative, such as in
# https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
MOVIE_URL_REGEX = rf"\/movies?\/{SLUG_REGEX}(?P<movie_key>{UUID_REGEX})"
# Any non-movie media-type prefix maps to a series, such as mini-series in
# https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
# or shows in
# https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
# The media-type path segment is any of them, e.g. show, shows, mini-series,
# limited-series.
SHOW_URL_REGEX = rf"\/[a-z-]+\/{SLUG_REGEX}(?:s\d+\/)?(?P<show_key>{UUID_REGEX})"


# TODO: Validate
class HBOMaxShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("HBO Max", "Max")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hbomax.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
