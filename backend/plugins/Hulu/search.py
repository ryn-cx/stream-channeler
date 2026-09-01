# TODO: Validate
"""Searching Hulu's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Hulu.files import FileMixin
from plugins.Hulu.utils import HuluMediaType, UtilsMixin


# TODO: Validate
class SearchMixin(UtilsMixin, FileMixin, register=False):
    """Searching Hulu."""

    # TODO: Validate
    @override
    def search_for_url(self, query: str) -> str | None:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        for group in search_file.parsed().groups:
            for result in group.results:
                media_type = result.metrics_info.target_type
                if media_type in (HuluMediaType.SERIES, HuluMediaType.MOVIE):
                    return self._show_url(
                        str(result.metrics_info.target_id),
                        HuluMediaType(media_type),
                    )
        return None
