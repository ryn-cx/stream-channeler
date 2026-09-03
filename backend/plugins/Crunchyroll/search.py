# TODO: Validate
from __future__ import annotations

from chirashi.search.models import Item as SearchItem

from app.media.media_type import TMDBMediaType
from plugins.Crunchyroll.constants import episode_is_music, show_is_an_artist
from plugins.Crunchyroll.files import FileMixin
from plugins.Crunchyroll.utils import UtilsMixin


# TODO: Validate
class SearchMixin(UtilsMixin, FileMixin):
    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        query = names[0]
        search_file = self.search_file(query)
        search_file.download_if_outdated()
        for datum in search_file.parsed().data:
            for item in datum.items:
                return self._search_result_url(item)
        return None

    # TODO: Validate
    def _search_result_url(self, item: SearchItem) -> str:
        item_key = item.id
        if show_is_an_artist(item_key):
            return self._artist_url(item_key)
        if episode_is_music(item_key) or item.type == "episode":
            return self._episode_url(item_key)
        return self._series_url(item_key)
