# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override
from urllib.parse import quote_plus

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.NHKWorld.search import SearchMixin
from plugins.NHKWorld.source import SourceMixin
from plugins.NHKWorld.upsert import UpsertMixin
from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class NHKWorldBase(SourceMixin, UpsertMixin, SearchMixin):
    # TODO: Add support for single episodes
    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"

    # TODO: Validate
    @classmethod
    @override
    def manual_search_url(cls, query: str) -> str:
        return cls.build_url(f"nhkworld/en/shows/search/?q={quote_plus(query)}")

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        program_file = self.video_program_file(show_key)
        program_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [TMDBLookupInfo(program_file.parsed().title, TMDBMediaType.tv, None)]
