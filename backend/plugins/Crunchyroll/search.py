# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from chirashi.search.models import Item as SearchItem

from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import is_music_episode_key, is_music_show_key


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    # TODO: Validate
    @override
    def search(self, query: str) -> str | None:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        for datum in search_file.parsed().data:
            for item in datum.items:
                return self._search_result_url(item)
        return None

    # TODO: Validate
    def _search_result_url(self, item: SearchItem) -> str:
        item_key = item.id
        if is_music_show_key(item_key):
            return self._artist_url(item_key)
        if is_music_episode_key(item_key) or item.type == "episode":
            return self._episode_url(item_key)
        return self._series_url(item_key)
