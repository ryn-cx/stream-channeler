# TODO: Validate
"""Searching HiDive's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override

from app.utils import tz_datetime
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.HiDive.utils import HelperMixin

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    """Searching HiDive."""

    MEDIA_TYPE_BY_SEARCH_TYPE: ClassVar = {
        "SERIES": SERIES_MEDIA_TYPE,
        "VOD": MOVIE_MEDIA_TYPE,
    }

    # TODO: Validate
    @override
    def search(self, query: str) -> str | None:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=30))
        for element in search_file.parsed().elements:
            for card in element.attributes.cards or []:
                type_prefix, _, key = card.attributes.action.data.id.partition("#")
                return self._show_url(
                    key,
                    self.MEDIA_TYPE_BY_SEARCH_TYPE[type_prefix],
                )
        return None
