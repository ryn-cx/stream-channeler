# TODO: Validate
from __future__ import annotations

from typing import override

from app.media.media_type import TMDBMediaType
from plugins.Roku.upsert import UpsertMixin


# TODO: Validate
class RokuBase(UpsertMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://therokuchannel.roku.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> tuple[str, TMDBMediaType | None, int | None]:
        return self.content_file(show_key).tmdb_lookup_info()
