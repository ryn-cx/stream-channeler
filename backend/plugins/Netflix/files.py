# TODO: Validate
import re
from collections.abc import Sequence
from functools import cache
from typing import override

from meshfilm import MeshFilm
from meshfilm.title import models as netflix_models

from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import GAPIJSON


@cache
def meshfilm() -> MeshFilm:
    return MeshFilm()


class Title(GAPIJSON[netflix_models.Title]):
    # Netflix serves a 404 for unknown title IDs.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = meshfilm().title


class FileMixin(BasePlugin, register=False):
    def title_file(self, title_key: str) -> Title:
        """Contains all of a Netflix title's data (show, seasons, episodes)."""
        return self._get_cached_file(
            Title,
            title_key,
            lambda: Title(self.session, self.plugin, title_key),
        )

    def _title(self, show_key: str) -> netflix_models.Title:
        return self.title_file(show_key).parsed()

    def _main_show(self, show_key: str) -> netflix_models.Show | None:
        return next(
            (
                show
                for show in self._title(show_key).shows
                if show.video_id == int(show_key)
            ),
            None,
        )

    def _main_movie(self, show_key: str) -> netflix_models.Movie | None:
        return next(
            (
                movie
                for movie in self._title(show_key).movies
                if movie.video_id == int(show_key)
            ),
            None,
        )

    def _is_movie(self, show_key: str) -> bool:
        return self._main_show(show_key) is None

    def _ordered_seasons(self, show_key: str) -> list[netflix_models.Season]:
        title = self._title(show_key)
        seasons_by_id = {season.video_id: season for season in title.seasons or []}
        main_show = self._main_show(show_key)
        if main_show and main_show.seasons:
            ordered_ids = [
                self._ref_video_id(edge.node.field__ref)
                for edge in main_show.seasons.edges
            ]
        else:
            ordered_ids = list(seasons_by_id)
        return [seasons_by_id[sid] for sid in ordered_ids if sid in seasons_by_id]

    def _season_episodes(
        self,
        show_key: str,
        season_id: int,
    ) -> list[netflix_models.Episode]:
        title = self._title(show_key)
        season = next(
            (season for season in title.seasons or [] if season.video_id == season_id),
            None,
        )
        if season is None:
            return []
        episodes_by_id = {episode.video_id: episode for episode in title.episodes or []}
        ordered_ids = [
            self._ref_video_id(edge.node.field__ref)
            for edge in season.episodes.edges
        ]
        return [episodes_by_id[eid] for eid in ordered_ids if eid in episodes_by_id]

    @staticmethod
    def _ref_video_id(ref: str) -> int:
        """Extract the videoId from a normalized GraphQL cache ref.

        Refs look like ``Season:{"videoId":80240028}``.
        """
        if match := re.search(r'"videoId":\s*(\d+)', ref):
            return int(match.group(1))
        msg = f"Could not extract videoId from ref: {ref}"
        raise ValueError(msg)

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
    def _show_files(self, show_key: str) -> Sequence[Title]:
        return [self.title_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[Title]:
        return [self.title_file(show_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[Title]:
        return [self.title_file(show_key)]

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
