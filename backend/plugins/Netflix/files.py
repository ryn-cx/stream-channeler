# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override

from meshfilm import Meshfilm
from meshfilm.lodp_title_and_plans_page import models as netflix_models
from meshfilm.search_page_results import models as search_models
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile
from plugins.utils.get_around_client import get_around_client


@cache
def meshfilm() -> Meshfilm:
    return Meshfilm(get_around_client=get_around_client())


class Title(GAPIJSON[netflix_models.LodpTitleAndPlansPageModel]):
    """Title file."""

    API_ENDPOINT = meshfilm().lodp_title_and_plans_page


class Search(GAPIJSON[search_models.SearchPageResultsModel]):
    """Search file."""

    API_ENDPOINT = meshfilm().search_page_results

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        cursor: str,
    ) -> None:
        self.query = query
        self.cursor = cursor
        super().__init__(session, plugin, f"{query}/{cursor}")

    @override
    def _get(self) -> search_models.SearchPageResultsModel:
        return meshfilm().search_page_results.download_and_parse(
            self.query,
            self.cursor or None,
        )


class FileMixin(TMDBMixin, register=False):
    def title_file(self, title_key: str) -> Title:
        """Contains all of a Netflix title's data (show, seasons, episodes)."""
        return self._file(Title, title_key)

    def search_file(self, query: str, cursor: str | None) -> Search:
        """Contains one page of Netflix's movie and TV search results."""
        return self._file(Search, query, cursor or "")

    def _title_video(self, show_key: str) -> netflix_models.Video1:
        parsed = self.title_file(show_key).parsed()
        video = next(
            (video for video in parsed.data.videos if video.video_id == int(show_key)),
            None,
        )
        if video is None:
            msg = f"No title found for {show_key}"
            raise ValueError(msg)
        return video

    def _is_movie(self, show_key: str) -> bool:
        return self._title_video(show_key).field__typename == "Movie"

    def _ordered_seasons(self, show_key: str) -> list[netflix_models.Node7]:
        seasons = self._title_video(show_key).seasons
        if seasons is None:
            return []
        return [edge.node for edge in seasons.edges]

    def _season_episodes(
        self,
        show_key: str,
        season_id: int,
    ) -> list[netflix_models.Node8]:
        for season in self._ordered_seasons(show_key):
            if season.video_id == season_id:
                return [edge.node for edge in season.episodes.edges]
        return []

    @staticmethod
    def _season_key(show_key: str, season_id: str | int) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single title file keyed by the show,
        but the base plugin resolves episode files from a season key alone, so
        the show key is carried inside it.
        """
        return f"{show_key}:{season_id}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self.title_file(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            [self.title_file(show_key)],
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
            [self.title_file(show_key)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, show_key)]
        return [
            self._season_key(show_key, season.video_id)
            for season in self._ordered_seasons(show_key)
        ]

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_id = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    str(episode.video_id)
                    for episode in self._season_episodes(show_key, int(season_id))
                ]
        return episode_keys
