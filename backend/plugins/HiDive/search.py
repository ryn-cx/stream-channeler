# TODO: Validate
"""Searching HiDive's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override

from diving_board.search import models as search_models

from app.utils import tz_datetime
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.HiDive.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    paginate_search_results,
)

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    """Searching HiDive."""

    MEDIA_TYPE_BY_SEARCH_TYPE: ClassVar = {
        "SERIES": SERIES_MEDIA_TYPE,
        "VOD": MOVIE_MEDIA_TYPE,
    }

    # HiDive answers a search with every match at once, so pages are cut out of
    # that one download rather than requested one at a time.
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=30)
        search_file.download_if_outdated(minimum_timestamp)

        results: list[PluginSearchResult] = []
        for element in search_file.parsed().elements:
            for card in element.attributes.cards or []:
                data = card.attributes.action.data
                type_prefix, _, key = data.id.partition("#")
                media_type = self.MEDIA_TYPE_BY_SEARCH_TYPE[type_prefix]
                results.append(
                    PluginSearchResult(
                        title=data.title,
                        url=self._show_url(key, media_type),
                        image_url=self._search_card_image(card),
                        media_type=media_type,
                        media_identifier=data.id,
                    ),
                )
        return paginate_search_results(results, cursor, self.search_page_size())

    # TODO: Validate
    @staticmethod
    def _search_card_image(card: search_models.Card) -> str:
        for header in card.attributes.header:
            if header.attributes.source:
                return header.attributes.source
        msg = "Search card has no image"
        raise ValueError(msg)
