# TODO: Validate
from abc import ABC
from collections.abc import Sequence
from functools import cache
from typing import Any, override
from uuid import UUID

from nana import Nana
from nana.content.models import ContentModel
from nana.content.models import Episode as ContentEpisode
from nana.content.models import Episode2 as SeasonEpisode
from nana.exceptions import ContentNotFoundError

from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile
from plugins.utils.get_around_client import get_around_client

MOVIE_TYPE = "movie"
SERIES_TYPE = "series"


@cache
def nana() -> Nana:
    return Nana(get_around_client=get_around_client())


def content_id(value: str | UUID) -> str:
    """Return a Roku content id as the 32 character string the API uses."""
    return value.hex if isinstance(value, UUID) else value


class BaseContentFile(GAPIJSON[ContentModel], ABC):
    API_ENDPOINT = nana().content


class ContentFile(BaseContentFile):
    """Content file."""

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)


class SeasonEpisodesFile(BaseContentFile):
    """Season episodes file."""


class FileMixin(TMDBMixin, register=False):
    def content_file(self, content_key: str) -> ContentFile:
        """Returns ContentFile file."""
        return self._file(ContentFile, content_key)

    def season_episodes_file(self, episode_key: str) -> SeasonEpisodesFile:
        """Returns SeasonEpisodesFile file."""
        return self._file(SeasonEpisodesFile, episode_key)

    def _content(self, content_key: str) -> ContentModel:
        return self.content_file(content_key).parsed()

    def _is_movie(self, show_key: str) -> bool:
        content_type = self._content(show_key).type
        if content_type not in (MOVIE_TYPE, SERIES_TYPE):
            msg = f"Invalid media type: {content_type}"
            raise RuntimeError(msg)
        return content_type == MOVIE_TYPE

    def _show_episodes(self, show_key: str) -> list[ContentEpisode]:
        return self._content(show_key).episodes or []

    def _season_numbers(self, show_key: str) -> list[int]:
        season_numbers: list[int] = []
        for episode in self._show_episodes(show_key):
            season_number = int(episode.season_number)
            if season_number not in season_numbers:
                season_numbers.append(season_number)
        return season_numbers

    def _first_episode_key(self, show_key: str, season_number: int) -> str:
        for episode in self._show_episodes(show_key):
            if int(episode.season_number) == season_number:
                return content_id(episode.meta.id)
        msg = f"No episodes for season {season_number} of {show_key}."
        raise ValueError(msg)

    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[SeasonEpisode]:
        episode_key = self._first_episode_key(show_key, season_number)
        season = self.season_episodes_file(episode_key).parsed().season
        if season is None:
            return []
        return season.episodes

    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    def _season_episodes_files(
        self,
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        if self._is_movie(show_key):
            return [self.content_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        episode_key = self._first_episode_key(show_key, season_number)
        return [self.season_episodes_file(episode_key)]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self.content_file(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            self._season_episodes_files(season_key, show_key),
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
            self._season_episodes_files(season_key, show_key),
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
        ]

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    content_id(episode.meta.id)
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
