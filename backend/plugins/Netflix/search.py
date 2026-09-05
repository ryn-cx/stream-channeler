# TODO: Validate
"""Searching Netflix's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.Netflix.files import FileMixin
from plugins.Netflix.utils import UtilsMixin


# TODO: Validate
class SearchMixin(UtilsMixin, FileMixin):
    """Searching Netflix."""

    # Netflix tags each search result with the media type of its title.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "Show": "Series",
        "Movie": "Movie",
    }

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        query = names[0]
        """Return the first movie or TV show Netflix matches `query` with.

        Netflix returns movies and shows intermixed. Suggestion entities
        (collections, autocomplete) carry no title and are skipped.
        """
        search_file = self.search_file(query, None)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=30))
        for section in search_file.parsed().data.page.sections.edges:
            for entity in section.node.entities.edges:
                unified_entity = entity.node.unified_entity
                if unified_entity is None:
                    continue
                if unified_entity.field__typename not in self._SEARCH_MEDIA_TYPES:
                    continue
                return self._show_url(str(unified_entity.video_id))
        return None
