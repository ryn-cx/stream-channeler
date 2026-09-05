# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.base_plugin_v3.base import BasePlugin, BaseReadURL

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
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        source_name = show.source.name or show.source.key
        show_name = f"{show.name} ({show.key})" if show.name else show.key
        logger.info("Updating show: {} - {}", source_name, show_name)
        stored_show = self._preload_show(show.key, source_key=show.source.key).one()
        self._update_and_upsert_show(stored_show, stored_show.update_at, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        stored_season = self._preload_season(season.id, preload_show=True).one()
        self._update_and_upsert_show(stored_season.show, stored_season.update_at)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        stored_episode = self._preload_episode(episode.id, preload_source=True).one()
        self._update_and_upsert_show(
            stored_episode.season.show,
            stored_episode.update_at,
        )


# TODO: Validate
class BaseImporter(BasePluginWorker, BaseReadURL, ABC):
    # TODO: Validate
    def _url_source(self) -> Source:
        return self._sources[self.plugin_name()]

    # TODO: Validate
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        if show := self._preload_show(media_info.show_key).one_or_none():
            return self._import_results(show, media_info)

        show = self.upsert_show(self._url_source(), media_info.show_key)
        return self._import_results(show, media_info)

    # TODO: Validate
    def on_failure(
        self,
        record: Show | Season | Episode,
        error: Exception,  # noqa: ARG002 - `error` is used by overrides.
    ) -> None:
        record.update_at = tz_datetime.max()
