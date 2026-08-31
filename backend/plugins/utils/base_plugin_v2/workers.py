# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.base import PluginBase, ReadURLBase

if TYPE_CHECKING:
    from app.shows.models import Show
    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class PluginWorker(PluginBase, ABC):
    # TODO: Validate
    def __init__(self, owner: PluginBase) -> None:
        super().__init__(owner.session)
        self._file_cache = owner._file_cache  # noqa: SLF001


# TODO: Validate
class URLImporter(PluginWorker, ReadURLBase, ABC):
    url: str

    # TODO: Validate
    def __init__(self, owner: PluginBase, url: str) -> None:
        super().__init__(owner)
        self.url = url
        self._parse_url(url)

    # TODO: Validate
    def _url_source(self) -> Source:
        return self._sources[self.plugin_name()]

    # TODO: Validate
    def import_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        if not force and (show := self._preload_show(show_key).one_or_none()):
            return self._import_results(show)

        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            if not force and (show := self._preload_show(show_key).one_or_none()):
                return self._import_results(show)

        show = self.upsert_show(
            self._url_source(),
            show_key,
            canonical_show=canonical_show,
            force=force,
        )
        return self._import_results(show)


# TODO: Validate
class Updater(PluginWorker, ABC):
    record: Show | Season | Episode

    # TODO: Validate
    def __init__(self, owner: PluginBase, record: Show | Season | Episode) -> None:
        super().__init__(owner)
        self.record = record

    # TODO: Validate
    @property
    def show(self) -> Show:
        record = self.record
        if isinstance(record, Season):
            return record.show
        if isinstance(record, Episode):
            return record.season.show
        return record

    # TODO: Validate
    def update(self, *, force: bool = False) -> None:
        record = self.record
        if isinstance(record, Season):
            self._update_season(record)
        elif isinstance(record, Episode):
            self._update_episode(record)
        else:
            self._update_show(record, force=force)

    # TODO: Validate
    def _update_show(self, show: Show, *, force: bool = False) -> None:
        source_name = show.source.name or show.source.key
        show_name = f"{show.name} ({show.key})" if show.name else show.key
        logger.info("Updating show: {} - {}", source_name, show_name)
        stored_show = self._preload_show(show.key, source_key=show.source.key).one()
        self._update_and_upsert_show(stored_show, stored_show.update_at, force=force)

    # TODO: Validate
    def _update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        stored_season = self._preload_season(season.id, preload_show=True).one()
        self._download_season_files_and_children(
            stored_season,
            update_at=stored_season.update_at,
        )
        self._update_and_upsert_show(stored_season.show)

    # TODO: Validate
    def _update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        stored_episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(
            stored_episode,
            update_at=stored_episode.update_at,
        )
        self._update_and_upsert_show(stored_episode.season.show)

    # TODO: Validate
    def on_failure(self, error: Exception) -> None:  # noqa: ARG002 - `error` is used by overrides.
        self.record.update_at = tz_datetime.max()
