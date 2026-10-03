# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.IMDb.linker import IMDbLinker
from plugins.IMDb.shared import IMDbShared
from plugins.IMDb.updater import IMDbUpdater
from plugins.TMDB import TMDB
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class IMDb(IMDbShared, BasePlugin, register=True):
    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[IMDbUpdater]:
        return IMDbUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[IMDbLinker]:
        return IMDbLinker

    # TODO: Validate
    @override
    def validate_and_import_url(self, url: str) -> list[URLImportResult]:
        tmdb = TMDB(self.session)
        tmdb_url = tmdb.tmdb_url_from_imdb_id(self.title_key_from_url(url))
        return tmdb.validate_and_import_url(tmdb_url)
