# TODO: Validate
"""What the plugin, its importers and its initializer all read Pluto TV by."""

from __future__ import annotations

from typing import override

from plugins.Pluto.basic_files import BasicFiles
from plugins.Pluto.constants import DETAILS_REGEX, ITEM_ID_REGEX, LOCALE_REGEX
from plugins.Pluto.utils import search_url

# https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details
# https://pluto.tv/us/on-demand/movies/68a54f49df1220b53566f16e
MOVIE_URL_REGEX = (
    rf"{LOCALE_REGEX}\/on-demand\/movies\/(?P<movie_key>{ITEM_ID_REGEX})"
    rf"{DETAILS_REGEX}(?:\/|$)"
)
# https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details
# https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1
# https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1/episode/5ef05c6ecdce3c001a779a95
SERIES_URL_REGEX = (
    rf"{LOCALE_REGEX}\/on-demand\/series\/(?P<series_key>{ITEM_ID_REGEX})"
    # The optional segments of a link that points at a season or an
    # episode of a series.
    rf"(?:\/season\/\d+(?:\/episode\/(?P<episode_key>{ITEM_ID_REGEX}))?)?"
    rf"{DETAILS_REGEX}(?:\/|$)"
)


# TODO: Validate
class PlutoShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
