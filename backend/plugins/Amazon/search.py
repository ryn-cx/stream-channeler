# TODO: Validate
"""Searching Prime Video's own catalogue."""

from __future__ import annotations

from datetime import timedelta

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.Amazon.files import FileMixin
from plugins.Amazon.utils import UtilsMixin


# TODO: Validate
class SearchMixin(UtilsMixin, FileMixin):
    """Searching Prime Video."""

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        query = names[0]
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        results = search_file.results()
        return self._detail_url(results[0]) if results else None
