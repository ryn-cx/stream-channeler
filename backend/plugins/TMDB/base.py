# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.TMDB.constants import TMDB_DOMAIN
from plugins.TMDB.listed_sources import ListedSourcesMixin
from plugins.TMDB.media_info import MediaInfoMixin
from plugins.TMDB.search import SearchMixin


# TODO: Validate
class TMDBBase(ListedSourcesMixin, SearchMixin, MediaInfoMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "TMDB"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN
