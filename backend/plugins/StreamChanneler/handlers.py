# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, override

from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.episodes.models import Episode
from app.plugins.models import Plugin as PluginModel
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult

if TYPE_CHECKING:
    import uuid

    from plugins.StreamChanneler import StreamChanneler


class StreamChannelerURLHandler(ABC):
    def __init__(self, plugin: StreamChanneler, url: str, media_id: uuid.UUID) -> None:
        self.plugin = plugin
        self.url = url
        self.media_id = media_id

    @abstractmethod
    def import_results(self) -> list[URLImportResult]: ...


class PluginURLHandler(StreamChannelerURLHandler):
    @override
    def import_results(self) -> list[URLImportResult]:
        plugin_entity = self.plugin.session.exec(
            select(PluginModel)
            .where(PluginModel.id == self.media_id)
            .options(joinedload(PluginModel.sources).joinedload(Source.shows)),  # type: ignore[arg-type]
        ).first()
        if not plugin_entity:
            msg = f"Plugin not found: {self.url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(show=show, is_whitelist=False)
            for source in plugin_entity.sources
            for show in source.shows
        ]


class SourceURLHandler(StreamChannelerURLHandler):
    @override
    def import_results(self) -> list[URLImportResult]:
        source = self.plugin.session.exec(
            select(Source)
            .where(Source.id == self.media_id)
            .options(joinedload(Source.shows)),  # type: ignore[arg-type]
        ).first()
        if not source:
            msg = f"Source not found: {self.url}"
            raise InvalidURLError(msg)
        return [URLImportResult(show=show, is_whitelist=False) for show in source.shows]


class ShowURLHandler(StreamChannelerURLHandler):
    @override
    def import_results(self) -> list[URLImportResult]:
        show = (
            self.plugin.session.exec(select(Show).where(Show.id == self.media_id))
            .unique()
            .first()
        )
        if not show:
            msg = f"Show not found: {self.url}"
            raise InvalidURLError(msg)
        return [URLImportResult(show=show, is_whitelist=False)]


class SeasonURLHandler(StreamChannelerURLHandler):
    @override
    def import_results(self) -> list[URLImportResult]:
        season = self.plugin.session.exec(
            select(Season)
            .where(Season.id == self.media_id)
            .options(joinedload(Season.show)),  # type: ignore[arg-type]
        ).first()
        if not season:
            msg = f"Season not found: {self.url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(show=season.show, seasons=[season], is_whitelist=True),
        ]


class EpisodeURLHandler(StreamChannelerURLHandler):
    @override
    def import_results(self) -> list[URLImportResult]:
        episode = self.plugin.session.exec(
            select(Episode)
            .where(Episode.id == self.media_id)
            .options(joinedload(Episode.season).joinedload(Season.show)),  # type: ignore[arg-type]
        ).first()
        if not episode:
            msg = f"Episode not found: {self.url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(
                show=episode.season.show,
                episodes=[episode],
                is_whitelist=True,
            ),
        ]
