# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override

from plugi import Plugi
from plugi.content.models import Child as ContentSeason
from plugi.content.models import Child1 as ContentEpisode
from plugi.content.models import ContentModel
from plugi.exceptions import ContentNotFoundError

from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile
from plugins.utils.get_around_client import get_around_client

# The `type` field of a Tubi content response marks a series; a movie and a single
# episode both use "v".
_SERIES_TYPE = "s"

# A movie has no seasons of its own so its single season is given a fixed id.
_MOVIE_SEASON_ID = "0"


@cache
def plugi() -> Plugi:
    return Plugi(get_around_client=get_around_client())


class ContentFile(GAPIJSON[ContentModel]):
    """Content file."""

    API_ENDPOINT = plugi().content

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid content_id {self.unique_identifier}"


class FileMixin(TMDBMixin, register=False):
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._file(ContentFile, content_id)

    def _content(self, content_id: str) -> ContentModel:
        return self.content_file(content_id).parsed()

    def _is_movie(self, show_key: str) -> bool:
        return self._content(show_key).type != _SERIES_TYPE

    def _seasons(self, show_key: str) -> list[ContentSeason]:
        children = self._content(show_key).children
        if children is None:
            return []
        # Tubi returns the seasons in an arbitrary order.
        return sorted(children, key=lambda season: int(season.id))

    def _season_episodes(self, show_key: str, season_id: str) -> list[ContentEpisode]:
        for season in self._seasons(show_key):
            if season.id == season_id:
                return season.children
        return []

    @staticmethod
    def _season_key(show_key: str, season_id: str) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single content file keyed by the show,
        but the base plugin resolves episode files from a season key alone, so the
        show key is carried inside it.
        """
        return f"{show_key}:{season_id}"

    @classmethod
    def _movie_season_key(cls, show_key: str) -> str:
        return cls._season_key(show_key, _MOVIE_SEASON_ID)

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self.content_file(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            [self.content_file(show_key)],
            season_key,
            show_key,
        )

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file(
            [self.content_file(show_key)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._movie_season_key(show_key)]
        return [
            self._season_key(show_key, season.id) for season in self._seasons(show_key)
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_id = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode.id for episode in self._season_episodes(show_key, season_id)
                ]
        return episode_keys
