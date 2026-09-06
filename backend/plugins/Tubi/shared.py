# TODO: Validate
"""What the plugin, its importers and its initializer all read Tubi by."""

from __future__ import annotations

from typing import override

from plugins.Tubi.base_files import TubiBaseFiles
from plugins.Tubi.constants import CONTENT_ID_REGEX, SLUG_REGEX
from plugins.Tubi.utils import search_url

# https://tubitv.com/movies/100029837/megamind
MOVIE_URL_REGEX = rf"\/movies\/(?P<movie_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
# https://tubitv.com/series/300006854/scooby-doo-where-are-you
SERIES_URL_REGEX = rf"\/series\/(?P<series_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
# https://tubitv.com/tv-shows/595036/s01-e01-what-a-night-for-a-knight
EPISODE_URL_REGEX = (
    rf"\/tv-shows\/(?P<episode_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
)


# TODO: Validate
class TubiShared(TubiBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Tubi"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
