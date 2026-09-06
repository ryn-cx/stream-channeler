# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.base_plugin.base import BasePlugin, BaseReadURL

if TYPE_CHECKING:
    from app.sources.models import Source
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class BasePluginWorker(BasePlugin, ABC):
    # TODO: Validate
    def __init__(self, owner: BasePlugin) -> None:
        super().__init__(owner.session)
        self._file_cache = owner._file_cache  # noqa: SLF001

    # TODO: Validate
    @override
    def update_title(self, title: Title, *, force: bool = False) -> None:
        source_name = title.source.name or title.source.key
        title_name = f"{title.name} ({title.key})" if title.name else title.key
        logger.info("Updating title: {} - {}", source_name, title_name)
        # TODO: Is this preload needed since _update_and_upsert_title preloads?c
        stored_title = self._preload_title(title.key, source_key=title.source.key).one()
        self._update_and_upsert_title(stored_title, stored_title.update_at, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        # TODO: Is this preload needed since _update_and_upsert_title preloads?c
        stored_season = self._preload_season(season.id, preload_title=True).one()
        self._update_and_upsert_title(stored_season.title, stored_season.update_at)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        # TODO: Is this preload needed since _update_and_upsert_title preloads?c
        stored_episode = self._preload_episode(episode.id, preload_source=True).one()
        self._update_and_upsert_title(
            stored_episode.season.title,
            stored_episode.update_at,
        )


# TODO: Validate
class BaseImporter(BasePluginWorker, BaseReadURL, ABC):
    # TODO: Validate
    def _url_source(self) -> Source:
        return self._sources[self.source_name()]

    # TODO: Validate
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        if title := self._preload_title(media_info.title_key).one_or_none():
            return self._import_results(title, media_info)

        title = self.upsert_title(self._url_source(), media_info.title_key)
        return self._import_results(title, media_info)

    # TODO: Validate
    def on_failure(
        self,
        record: Title | Season | Episode,
        error: Exception,  # noqa: ARG002 - `error` is used by overrides.
    ) -> None:
        record.update_at = tz_datetime.max()
