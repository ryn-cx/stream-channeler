# TODO: Validate
from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING, override

from plugins.StreamChanneler.base import StreamChannelerBase
from plugins.StreamChanneler.files import FileMixin
from plugins.StreamChanneler.handlers import (
    EpisodeURLHandler,
    PluginURLHandler,
    SeasonURLHandler,
    ShowURLHandler,
    SourceURLHandler,
    StreamChannelerURLHandler,
)
from plugins.StreamChanneler.initialize import StreamChannelerInitializer
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class StreamChanneler(StreamChannelerBase, FileMixin, AbstractPlugin):
    initializer = StreamChannelerInitializer

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
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        return self.get_url_handler(url).import_results()

    # TODO: Validate
    def get_url_handler(self, url: str) -> StreamChannelerURLHandler:
        match = re.match(self.url_regex(), url)
        if not match:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
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
