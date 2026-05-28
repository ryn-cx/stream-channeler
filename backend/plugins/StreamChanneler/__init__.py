# TODO: Validate
import re
import uuid
from collections.abc import Callable, Sequence
from typing import Any, override

from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.episodes.models import Episode
from app.plugins.models import Plugin as PluginModel
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile


class StreamChanneler(BasePlugin, register=True):
    _VERSION = "0.0.1"

    # StreamChanneler does not use files, so these abstract methods are no-ops.

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return []

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        return []

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        msg = "StreamChanneler does not support upserting shows"
        raise NotImplementedError(msg)

    @classmethod
    @override
    def domains(cls) -> list[str]:
        # localhost is added for developement purposes.
        return ["streamchanneler.com", "localhost"]

    @classmethod
    @override
    def _url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        return (
            domain_regex
            + r"\/(?P<media_type>plugin|source|show|season|episode)"
            + rf"\/(?P<media_id>{uuid_pattern})(?:\/|$)"
        )

    @classmethod
    @override
    def parse_url(cls, url: str) -> dict[str, str]:
        match = re.match(cls._url_regex(), url)
        if not match:
            msg = f"Invalid {cls.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
        return {
            "media_type": match.group("media_type"),
            "media_id": match.group("media_id"),
        }

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self.parse_url(url)
        media_type = parsed["media_type"]
        media_id = uuid.UUID(parsed["media_id"])

        handlers: dict[str, Callable[[uuid.UUID, str], list[URLImportResult]]] = {
            "show": self._import_show,
            "season": self._import_season,
            "episode": self._import_episode,
            "source": self._import_source,
            "plugin": self._import_plugin,
        }
        return handlers[media_type](media_id, url)

    def _import_plugin(
        self,
        plugin_id: uuid.UUID,
        url: str,
    ) -> list[URLImportResult]:
        plugin_entity = self.session.exec(
            select(PluginModel)
            .where(PluginModel.id == plugin_id)
            .options(joinedload(PluginModel.sources).joinedload(Source.shows)),  # type: ignore[arg-type]
        ).first()
        if not plugin_entity:
            msg = f"Plugin not found: {url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(show=show, is_whitelist=False)
            for source in plugin_entity.sources
            for show in source.shows
        ]

    def _import_source(
        self,
        source_id: uuid.UUID,
        url: str,
    ) -> list[URLImportResult]:
        source = self.session.exec(
            select(Source)
            .where(Source.id == source_id)
            .options(
                joinedload(Source.shows),  # type: ignore[arg-type]
            ),
        ).first()
        if not source:
            msg = f"Source not found: {url}"
            raise InvalidURLError(msg)
        return [URLImportResult(show=show, is_whitelist=False) for show in source.shows]

    def _import_show(
        self,
        show_id: uuid.UUID,
        url: str,
    ) -> list[URLImportResult]:
        show = (
            self.session.exec(select(Show).where(Show.id == show_id)).unique().first()
        )

        if not show:
            msg = f"Show not found: {url}"
            raise InvalidURLError(msg)
        return [URLImportResult(show=show, is_whitelist=False)]

    def _import_season(
        self,
        season_id: uuid.UUID,
        url: str,
    ) -> list[URLImportResult]:
        season = self.session.exec(
            select(Season)
            .where(Season.id == season_id)
            .options(joinedload(Season.show)),  # type: ignore[arg-type]
        ).first()
        if not season:
            msg = f"Season not found: {url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(show=season.show, seasons=[season], is_whitelist=True),
        ]

    def _import_episode(
        self,
        episode_id: uuid.UUID,
        url: str,
    ) -> list[URLImportResult]:
        episode = self.session.exec(
            select(Episode)
            .where(Episode.id == episode_id)
            .options(joinedload(Episode.season).joinedload(Season.show)),  # type: ignore[arg-type]
        ).first()
        if not episode:
            msg = f"Episode not found: {url}"
            raise InvalidURLError(msg)
        return [
            URLImportResult(
                show=episode.season.show,
                episodes=[episode],
                is_whitelist=True,
            ),
        ]
