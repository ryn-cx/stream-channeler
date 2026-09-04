# TODO: Validate
from __future__ import annotations

from typing import override

from app.media.media_type import TMDBMediaType
from plugins.Tubi.upsert import UpsertMixin


# TODO: Validate
class TubiBase(UpsertMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Tubi"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> tuple[str, TMDBMediaType | None, int | None]:
        return self.content_file(show_key).tmdb_lookup_info()
