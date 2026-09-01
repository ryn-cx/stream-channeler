# TODO: Validate
from __future__ import annotations

from datetime import timedelta

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin


# TODO: Validate
class SearchMixin(FileMixin):
    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: MediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        query = names[0]
        search_file = self.shows_search_file(query, 0)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hits = search_file.parsed().hits.hits
        return self.build_url(hits[0].field_source.url) if hits else None
