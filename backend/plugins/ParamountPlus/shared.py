# TODO: Validate
"""What the plugin, its importers and its initializer all read Paramount+ by."""

from __future__ import annotations

from typing import override

from plugins.ParamountPlus.base_files import ParamountPlusBaseFiles
from plugins.ParamountPlus.utils import search_url

# https://www.paramountplus.com/movies/video/ALVE01KT235XQDEK58R7H2012VNZMK/
MOVIE_URL_REGEX = r"\/movies\/video\/(?P<movie_key>[A-Za-z0-9]+)(?:\/|$)"
# https://www.paramountplus.com/shows/south-park/
TITLE_URL_REGEX = r"\/shows\/(?P<title_key>[a-z0-9-]+)(?:\/|$)"


# TODO: Validate
class ParamountPlusShared(ParamountPlusBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (
            "Paramount Plus",
            "Paramount+",
            "Paramount+ Amazon Channel",
            "Paramount Plus Essential",
            "Paramount Plus Premium",
        )

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.paramountplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:  # noqa: ARG003 - Paramount+ carries no query in a search address.
        return search_url()
