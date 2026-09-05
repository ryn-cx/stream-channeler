# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Netflix.search import SearchMixin
from plugins.Netflix.upsert import UpsertMixin
from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class NetflixBase(UpsertMixin, SearchMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Netflix"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Netflix", "Netflix Standard with Ads")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.netflix.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        return self.title_file(show_key).tmdb_lookup_info()
