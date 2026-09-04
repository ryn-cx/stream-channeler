# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from app.episodes.models import Episode
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.base import BasePlugin, BaseReadURL

if TYPE_CHECKING:
    from app.shows.models import Show
    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class BasePluginWorker(BasePlugin, ABC):
    # TODO: Validate
    def __init__(self, owner: BasePlugin) -> None:
        super().__init__(owner.session)
        self._file_cache = owner._file_cache  # noqa: SLF001


# TODO: Validate
class BaseImporter(BasePluginWorker, BaseReadURL, ABC):
    # TODO: Validate
    def _url_source(self) -> Source:
        return self._sources[self.plugin_name()]

    # TODO: Validate
    def import_url(
        self,
        url: str,
        *,
        known_title: bool = False,  # noqa: ARG002
    ) -> list[URLImportResult]:
        show_key = self._url_to_show_key(url)
        if show := self._preload_show(show_key).one_or_none():
            return self._import_results(show)

        _cache = self._download_show_files_and_children(show_key)
        show = self.upsert_show(self._url_source(), show_key)
        return self._import_results(show)

    # TODO: Validate
    def on_failure(
        self,
        record: Show | Season | Episode,
        error: Exception,  # noqa: ARG002 - `error` is used by overrides.
    ) -> None:
        record.update_at = tz_datetime.max()
