# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from chirashi.search import models as search_models

from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)


class SearchMixin(HelperMixin, register=False):
    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        items = [
            item
            for datum in parsed.data
            if datum.type != "top_results"
            for item in datum.items
        ]
        items.sort(key=lambda item: item.search_metadata.score, reverse=True)
        results = [
            PluginSearchResult(
                title=item.title,
                url=self._show_url(item.id),
                year=item.series_metadata.series_launch_year
                if item.series_metadata
                else None,
                image_url=self._search_image_url(item.images),
                media_type=item.type.replace("_", " ").title(),
            )
            for item in items
        ]
        return PluginSearchResults(results=results)

    @staticmethod
    def _search_image_url(images: search_models.Images) -> str | None:
        for group in (
            images.poster_tall,
            images.promo_image,
            images.poster_wide,
            images.thumbnail,
        ):
            if group:
                variants = group[0]
                image = variants[1] if isinstance(variants, list) else variants
                return image.source
        return None
