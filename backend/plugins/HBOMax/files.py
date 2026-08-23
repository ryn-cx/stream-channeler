# TODO: Validate
"""The files HBO Max is read out of."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Any, ClassVar, override

from minbo import MinBO
from minbo.exceptions import MovieNotFoundError, ShowNotFoundError
from minbo.movie import Movie as MovieEndpoint
from minbo.movie.models import Idref14 as MovieContent
from minbo.movie.models import MovieModel
from minbo.show import Show as ShowEndpoint
from minbo.show.models import Episode, Season, ShowModel
from minbo.show.models import Idref14 as ShowContent

from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointFile
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def minbo() -> MinBO:
    """Return a cached MinBO client."""
    return MinBO(get_around_client=get_around_client())


# TODO: Validate
class ShowFile(EndpointFile[ShowModel]):
    """Show file."""

    API_ENDPOINT: ClassVar[ShowEndpoint] = minbo().show

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class SeasonFile(EndpointFile[ShowModel]):
    """Season file."""

    API_ENDPOINT: ClassVar[ShowEndpoint] = minbo().show

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
        return self.API_ENDPOINT.download(self.show_id, self.season_number)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class MovieFile(EndpointFile[MovieModel]):
    """Movie file."""

    API_ENDPOINT: ClassVar[MovieEndpoint] = minbo().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def show_file(self, show_id: str) -> ShowFile:
        """Return ShowFile file."""
        return self._file(ShowFile, show_id)

    # TODO: Validate
    def season_file(self, show_id: str, season_number: int) -> SeasonFile:
        """Return SeasonFile file."""
        return self._file(SeasonFile, show_id, season_number)

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
    @staticmethod
    def _episode_key(season_key: str, episode_number: int) -> str:
        return f"{season_key}:{episode_number}"

    # TODO: Validate
    def _show_content(self, show_id: str) -> ShowContent:
        return self.show_file(show_id).parsed().props.page_props.mapped_data.idref14

    # TODO: Validate
    def _season_numbers(self, show_id: str) -> list[int]:
        return [season.season_number for season in self._show_content(show_id).seasons]

    # TODO: Validate
    def _season_entry(self, show_id: str, season_number: int) -> Season:
        for season in self._show_content(show_id).seasons:
            if season.season_number == season_number:
                return season
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    # TODO: Validate
    def _season_episodes(
        self,
        show_id: str,
        season_number: int,
    ) -> list[Episode]:
        content = (
            self.season_file(show_id, season_number)
            .parsed()
            .props.page_props.mapped_data.idref14
        )
        for season in content.seasons:
            if season.season_number == season_number:
                return season.episodes
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    # TODO: Validate
    def _movie_content(self, movie_id: str) -> MovieContent:
        return self.movie_file(movie_id).parsed().props.page_props.mapped_data.idref14

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        # Required to detect changes to the show and new seasons of it.
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        # Required to detect changes to the season and new episodes of it.
        return [self.season_file(show_key, season_number)]

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
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return [self.season_file(show_key, season_number)]

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
                    self._episode_key(season_key, episode.episode_number)
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
