# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.DisneyPlus.upsert import UpsertMixin
from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class DisneyPlusBase(UpsertMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.disneyplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        return self.entity_file(show_key).tmdb_lookup_info()
