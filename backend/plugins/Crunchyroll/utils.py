# TODO: Validate

from typing import override
from urllib.parse import quote_plus

from chirashi.series.models import Datum as SeriesDatum

from app.media.media_type import MediaType
from app.sources.models import Source
from plugins.Crunchyroll.constants import (
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    episode_is_music,
    music_episode_category,
)
from plugins.Crunchyroll.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    @property
    def video_source(self) -> Source:
        """Return the plugin's video `Source`.

        This is a property so the `Source` will be cached."""
        return self._source_db_entry(VIDEO_SOURCE)

    @property
    def music_source(self) -> Source:
        """Return the plugin's music `Source`.

        This is a property so the `Source` will be cached."""
        return self._source_db_entry(MUSIC_SOURCE)

    # TODO: Validate
    def _series_datum(self, show_key: str) -> SeriesDatum:
        return self.series_file(show_key).parsed().data[0]

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return "type:movie" in self._series_datum(show_key).keywords

    # TODO: Validate
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie(show_key) else MediaType.tv

    # TODO: Validate
    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    # TODO: Validate
    @classmethod
    def _artist_url(cls, show_key: str) -> str:
        return cls.build_url(f"artist/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        # Crunchyroll files a music video or a concert under the listing it
        # belongs to, which its id says but the url still has to be told.
        if episode_is_music(episode_key):
            category = music_episode_category(episode_key)
            return cls.build_url(f"watch/{category}/{episode_key}")
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @classmethod
    @override
    def manual_search(cls, query: str) -> str:
        return cls.build_url(f"search?q={quote_plus(query)}")
