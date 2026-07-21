# TODO: Validate
from collections.abc import Sequence
from typing import Any, Literal, override

from app.shows.models import Show
from plugins.TMDB import TMDB
from plugins.TMDB.files import EpisodeDetail, MovieDetails, SeasonDetail, ShowDetail
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile


class TMDBMixin(BasePlugin, register=False):
    """Wraps TMDB files so they files are downloaded for the TMDB plugin."""

    @property
    def tmdb(self) -> TMDB:
        """Return the TMDB plugin instance."""
        if not hasattr(self, "_tmdb_plugin"):
            self._tmdb_plugin = TMDB(self.session)
        return self._tmdb_plugin

    def _tmdb_search_media(
        self,
        title: str,
        media_type: Literal["movie", "tv"] | None = "tv",
        year: int | None = None,
    ) -> int | None:
        """Return the best-match TMDB id for a title, or None.

        `media_type` restricts the search to movies or tv series; pass None to
        consider both and take the better title match. `year` narrows movie and
        tv searches to a release/first-air year.
        """
        results = (
            self.tmdb.auto_updating_search_media(media_type, title, year)
            .parsed()
            .results
        )
        return results[0].id if results else None

    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        raise NotImplementedError

    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        raise NotImplementedError

    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        raise NotImplementedError

    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:  # noqa: ARG002
        return "tv"

    def _tmdb_show_file(self, show_key: str) -> ShowDetail | MovieDetails | None:
        tmdb_id = self._fetch_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self._tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        return self.tmdb.show_detail_file(tmdb_id)

    def _tmdb_season_file(
        self,
        season_key: str,
        show_key: str,
    ) -> SeasonDetail | MovieDetails | None:
        tmdb_id = self._fetch_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self._tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        season_number = self._get_season_number(season_key, show_key)
        if season_number is None:
            return None
        if not self.tmdb.has_season(tmdb_id, season_number):
            return None
        return self.tmdb.season_detail_file(tmdb_id, season_number)

    def _tmdb_episode_file(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> EpisodeDetail | MovieDetails | None:
        tmdb_id = self._fetch_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self._tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        season_number = self._get_season_number(season_key, show_key)
        episode_number = self._get_episode_number(episode_key, season_key, show_key)
        if not (season_number and episode_number):
            return None
        if not self.tmdb.has_episode(tmdb_id, season_number, episode_number):
            return None
        return self.tmdb.episode_detail_file(tmdb_id, season_number, episode_number)

    def _append_tmdb_show_file(
        self,
        files: Sequence[BaseFile[Any]],
        show_key: str,
    ) -> list[BaseFile[Any]]:
        tmdb_file = self._tmdb_show_file(show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    def _append_tmdb_season_file(
        self,
        files: Sequence[BaseFile[Any]],
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        tmdb_file = self._tmdb_season_file(season_key, show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    def _append_tmdb_episode_file(
        self,
        files: Sequence[BaseFile[Any]],
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        tmdb_file = self._tmdb_episode_file(episode_key, season_key, show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file([], season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file([], episode_key, season_key, show_key)
