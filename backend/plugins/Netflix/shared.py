# TODO: Validate
"""What the plugin, its importers and its initializer all read Netflix by."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.media.media_type import TMDBMediaType
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Netflix.base_files import NetflixBaseFiles
from plugins.Netflix.utils import first_search_result_key, search_url, title_url

TITLE_URL_REGEX = r"\/title\/(?P<title_key>\d+)(?:\/|$)"


# TODO: Validate
class NetflixShared(NetflixBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Netflix"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Netflix", "Netflix Standard with Ads")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.netflix.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        search_file = self.search_file(names[0], None)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=30))
        title_key = first_search_result_key(search_file.parsed())
        if title_key is None:
            return None
        return title_url(title_key)
