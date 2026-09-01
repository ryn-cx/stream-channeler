# TODO: Validate
"""Searching Prime Video's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Amazon.files import FileMixin
from plugins.Amazon.utils import UtilsMixin


# TODO: Validate
class SearchMixin(UtilsMixin, FileMixin):
    """Searching Prime Video."""

    # TODO: Validate
    @override
    def search_for_url(self, query: str) -> str | None:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        results = search_file.results()
        return self._detail_url(results[0]) if results else None
