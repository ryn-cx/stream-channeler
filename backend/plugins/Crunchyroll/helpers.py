# TODO: Validate

from typing import Any

from app.media.media_type import MediaType
from app.sources.models import Source
from plugins.Crunchyroll.files import FileMixin
from plugins.Crunchyroll.music_keys import (
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    is_music_episode_key,
    is_music_show_key,
    music_episode_category,
)


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    @property
    def video_source(self) -> Source:
        return self._source_record(VIDEO_SOURCE)

    # TODO: Validate
    @property
    def music_source(self) -> Source:
        return self._source_record(MUSIC_SOURCE)

    # TODO: Validate
    def _source_from_show_key(self, show_key: str) -> Source:
        if is_music_show_key(show_key):
            return self.music_source
        return self.video_source

    # TODO: Validate
    def _series_datum(self, show_key: str) -> dict[str, Any]:
        series_file = self.series_file(show_key)
        datum: dict[str, Any] = series_file.parsed()["data"][0]
        return datum

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return "type:movie" in self._series_datum(show_key)["keywords"]

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
        if is_music_episode_key(episode_key):
            category = music_episode_category(episode_key)
            return cls.build_url(f"watch/{category}/{episode_key}")
        return cls.build_url(f"watch/{episode_key}")
