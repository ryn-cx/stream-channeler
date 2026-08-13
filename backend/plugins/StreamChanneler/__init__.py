# TODO: Validate
from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Any, override

from app.shows.models import Show
from app.sources.models import Source
from plugins.StreamChanneler.handlers import (
    EpisodeURLHandler,
    PluginURLHandler,
    SeasonURLHandler,
    ShowURLHandler,
    SourceURLHandler,
    StreamChannelerURLHandler,
)
from plugins.StreamChanneler.watch_history import WatchHistoryMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class StreamChanneler(WatchHistoryMixin, BasePlugin, register=True):
    _VERSION = "0.0.1"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Stream Channeler"

    # StreamChanneler does not use files, so these abstract methods are no-ops.

    # TODO: Validate
    @override
    def initialize_sources(self) -> None:
        return

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        return []

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        msg = "StreamChanneler does not support upserting shows"
        raise NotImplementedError(msg)

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        # localhost is added for developement purposes.
        return ["streamchanneler.com", "localhost"]

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        return (
            domain_regex
            + r"\/(?P<media_type>plugin|source|show|season|episode)"
            + rf"\/(?P<media_id>{uuid_pattern})(?:\/|$)"
        )

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,  # noqa: ARG002 - Copies media that already carries its own link.
    ) -> list[URLImportResult]:
        return self.get_url_handler(url).import_results()

    # TODO: Validate
    def get_url_handler(self, url: str) -> StreamChannelerURLHandler:
        match = re.match(self.url_regex(), url)
        if not match:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
        handlers: dict[str, type[StreamChannelerURLHandler]] = {
            "plugin": PluginURLHandler,
            "source": SourceURLHandler,
            "show": ShowURLHandler,
            "season": SeasonURLHandler,
            "episode": EpisodeURLHandler,
        }
        handler_class = handlers[match.group("media_type")]
        return handler_class(self, url, uuid.UUID(match.group("media_id")))
