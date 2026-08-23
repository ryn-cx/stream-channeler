# TODO: Validate
"""The files Paramount+ is read out of."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from typing import Any, ClassVar, override

from sqlmodel import Session
from trivial_minus import TrivialMinus
from trivial_minus.episodes import Episodes as EpisodesEndpoint
from trivial_minus.episodes.models import Datum, EpisodesModel
from trivial_minus.exceptions import MovieNotFoundError, ShowNotFoundError
from trivial_minus.movie import Movie as MovieEndpoint
from trivial_minus.movie.models import MovieModel
from trivial_minus.show import Show as ShowEndpoint
from trivial_minus.show.models import ShowModel

from app.plugins.models import Plugin
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointFile
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def trivial_minus() -> TrivialMinus:
    return TrivialMinus(get_around_client=get_around_client())


# TODO: Validate
class ShowPage(EndpointFile[ShowModel]):
    """Show page file."""

    API_ENDPOINT: ClassVar[ShowEndpoint] = trivial_minus().show

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".html"

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid show {self.unique_identifier}"

    # TODO: Validate
    def season_numbers(self) -> list[int]:
        """Return the show's available season numbers, sorted ascending."""
        return self.parsed().seasons


# TODO: Validate
class EpisodesFile(EndpointFile[EpisodesModel]):
    """Episodes file."""

    API_ENDPOINT: ClassVar[EpisodesEndpoint] = trivial_minus().episodes

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_id: str,
        season_number: int,
    ) -> None:
        """Initialize the file."""
        self.show_id = show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{show_id}/{season_number}")

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(
            self.show_id,
            season_number=self.season_number,
        )


# TODO: Validate
class MovieFile(EndpointFile[MovieModel]):
    """Movie file."""

    API_ENDPOINT: ClassVar[MovieEndpoint] = trivial_minus().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid movie_id {self.unique_identifier}"


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def show_page_file(self, show_id: str) -> ShowPage:
        """Return ShowPage file."""
        return self._file(ShowPage, show_id)

    # TODO: Validate
    def episodes_file(self, show_id: str, season_number: int) -> EpisodesFile:
        """Return EpisodesFile file."""
        return self._file(EpisodesFile, show_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        """Return MovieFile file."""
        return self._file(MovieFile, movie_id)

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)
        return self._media_type_value == "movie"

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    # TODO: Validate
    def _season_numbers(self, show_id: str) -> list[int]:
        return self.show_page_file(show_id).season_numbers()

    # TODO: Validate
    def _season_episodes(
        self,
        show_id: str,
        season_number: int,
    ) -> list[Datum]:
        return self.episodes_file(show_id, season_number).parsed().result.data

    # TODO: Validate
    def _movie_data(self, movie_id: str) -> MovieModel:
        return self.movie_file(movie_id).parsed()

    # TODO: Validate
    def _series_title(self, show_id: str) -> str:
        first_season = self._season_numbers(show_id)[0]
        self.episodes_file(show_id, first_season).download_if_outdated()
        return self._season_episodes(show_id, first_season)[0].series_title

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        # Required to detect new seasons.
        return [self.show_page_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        # Required to detect new episodes.
        return [self.episodes_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        return [self.episodes_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
        ]

    # TODO: Validate
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
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode.content_id
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
