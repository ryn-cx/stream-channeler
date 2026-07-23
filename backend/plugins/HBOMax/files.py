# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override

from minbo import MinBO
from minbo.movies.models import MoviesModel
from minbo.show.models import Episode1 as ShowEpisode
from minbo.show.models import Idref14 as ShowContent
from minbo.show.models import Season1 as ShowSeason
from minbo.show.models import ShowModel
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, PartialGAPIJSON
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


@cache
def minbo() -> MinBO:
    return MinBO(get_around_client=get_around_client())


class ShowFile(GAPIJSON[ShowModel]):
    API_ENDPOINT = minbo().show


class SeasonFile(PartialGAPIJSON[ShowModel]):
    API_ENDPOINT = minbo().show

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_id: str,
        season_number: int,
    ) -> None:
        self.show_id = show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{show_id}/{season_number}")

    @override
    def _get(self) -> ShowModel:
        return self.API_ENDPOINT.download_and_parse(
            self.show_id,
            season_number=self.season_number,
        )


class MovieFile(GAPIJSON[MoviesModel]):
    API_ENDPOINT = minbo().movie


class FileMixin(MediaTypeMixin, TMDBMixin, register=False):
    def show_file(self, show_id: str) -> ShowFile:
        return self._get_cached_file(
            ShowFile,
            show_id,
            lambda: ShowFile(self.session, self.plugin, show_id),
        )

    def season_file(self, show_id: str, season_number: int) -> SeasonFile:
        return self._get_cached_file(
            SeasonFile,
            (show_id, season_number),
            lambda: SeasonFile(self.session, self.plugin, show_id, season_number),
        )

    def movie_file(self, movie_id: str) -> MovieFile:
        return self._get_cached_file(
            MovieFile,
            movie_id,
            lambda: MovieFile(self.session, self.plugin, movie_id),
        )

    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == "movie"

    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    @staticmethod
    def _episode_key(season_key: str, episode_number: int) -> str:
        return f"{season_key}:{episode_number}"

    @staticmethod
    def _split_episode_key(episode_key: str) -> tuple[str, int]:
        season_key, _, episode_number = episode_key.rpartition(":")
        return season_key, int(episode_number)

    @staticmethod
    def _content(model: ShowModel) -> ShowContent:
        return model.props.page_props.mapped_data.idref14

    def _show_content(self, show_id: str) -> ShowContent:
        return self._content(self.show_file(show_id).parsed())

    def _season_numbers(self, show_id: str) -> list[int]:
        return [season.season_number for season in self._show_content(show_id).seasons]

    def _season_entry(self, show_id: str, season_number: int) -> ShowSeason:
        for season in self._show_content(show_id).seasons:
            if season.season_number == season_number:
                return season
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    def _season_episodes(self, show_id: str, season_number: int) -> list[ShowEpisode]:
        content = self._content(self.season_file(show_id, season_number).parsed())
        for season in content.seasons:
            if season.season_number == season_number:
                return season.episodes
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            base_files = [self.show_file(show_key)]
        return self._append_tmdb_show_file(base_files, show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            _, season_number = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_number)]
        return self._append_tmdb_season_file(base_files, season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            _, season_number = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_number)]
        return self._append_tmdb_episode_file(
            base_files,
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
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
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    self._episode_key(season_key, episode.episode_number)
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
