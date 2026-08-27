# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from chirashi.search.models import Images as SearchImages
from chirashi.search.models import Item as SearchItem
from chirashi.search.models import SearchModel

from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import is_music_episode_key, is_music_show_key
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    paginate_search_results,
)


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    # Crunchyroll answers a search with every match at once, so pages are cut out
    # of that one download rather than requested one at a time.
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        results = [
            PluginSearchResult(
                title=item.title,
                url=self._search_result_url(item),
                year=item.series_metadata.series_launch_year
                if item.series_metadata
                else None,
                image_url=self._search_image_url(item.images),
                media_type=item.type.replace("_", " ").title(),
                media_identifier=item.id,
            )
            for item in self._search_items(parsed)
        ]
        return paginate_search_results(results, cursor, self.search_page_size())

    # TODO: Validate
    @staticmethod
    def _search_items(parsed: SearchModel) -> list[SearchItem]:
        top_results = [
            item
            for datum in parsed.data
            if datum.type == "top_results"
            for item in datum.items
        ]
        remaining = [
            item
            for datum in parsed.data
            if datum.type != "top_results"
            for item in datum.items
        ]
        remaining.sort(key=lambda item: item.search_metadata.score, reverse=True)
        ranked = {item.id for item in top_results}
        return top_results + [item for item in remaining if item.id not in ranked]

    # TODO: Validate
    def _search_result_url(self, item: SearchItem) -> str:
        item_key = item.id
        if is_music_show_key(item_key):
            return self._artist_url(item_key)
        if is_music_episode_key(item_key) or item.type == "episode":
            return self._episode_url(item_key)
        return self._series_url(item_key)

    # TODO: Validate
    @staticmethod
    def _search_image_url(images: SearchImages) -> str | None:
        for group in (images.poster_tall, images.promo_image, images.poster_wide):
            if group:
                return group[0][1].source
        if images.thumbnail:
            variants = images.thumbnail[0]
            if isinstance(variants, list):
                return variants[1].source
            return variants.source
        return None
