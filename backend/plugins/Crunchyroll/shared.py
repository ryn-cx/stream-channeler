# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Crunchyroll.base_files import CrunchyrollBaseFiles
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE

if TYPE_CHECKING:
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class CrunchyrollShared(CrunchyrollBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        # Do not use the year for Crunchyroll because it's so often incorrect. It's fine
        # to leave it in the database as a reference but using it for lookups keeps
        # returning the wrong results.
        return [
            lookup_info._replace(year=None)
            for lookup_info in super().tmdb_lookup_info(title)
        ]
