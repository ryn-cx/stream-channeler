from __future__ import annotations

from typing import override

from plugins.TMDB.listed_sources import ListedSourcesMixin
from plugins.TMDB.media_info import MediaInfoMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.urls import TMDB_DOMAIN


class TMDBBase(ListedSourcesMixin, SearchMixin, MediaInfoMixin):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "TMDB"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN
