# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.utils.base_plugin.linker import BasePluginLinker

if TYPE_CHECKING:
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class CrunchyrollLinker(CrunchyrollShared, BasePluginLinker):
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
