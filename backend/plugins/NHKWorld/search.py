# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin


# TODO: Validate
class SearchMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def search(self, query: str) -> str | None:
        search_file = self.shows_search_file(query, 0)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hits = search_file.parsed().hits.hits
        return self.build_url(hits[0].field_source.url) if hits else None
