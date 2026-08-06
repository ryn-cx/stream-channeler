# TODO: Validate
from collections.abc import Sequence
from typing import Any, Literal, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils.sentinels import Sentinel
from plugins.TMDB import TMDB
from plugins.TMDB.files import EpisodeDetail, MovieDetails, SeasonDetail, ShowDetail
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile

_UNRESOLVED = Sentinel("TMDB_ID")


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

    def _merge_and_upsert_show(
        self,
        show: Show,
        source: Source,
        existing_show: Show | None,
        show_key: str,
        tmdb_media_type: Literal["movie", "tv"],
    ) -> Show:
        """Store the website's own `Show`, pointed at the TMDB title behind it.

        Nothing is copied off TMDB here. The title is imported as the TMDB
        plugin's own media instead, which is what fills in whatever this website
        leaves out when the `Show` is served.
        """
        tmdb_id = self._fetch_tmdb_id(show_key, existing_show)
        show = self.tmdb.tmdb_link_show(show, tmdb_id, tmdb_media_type)
        if show.tmdb_id:
            self.tmdb.import_title(tmdb_media_type, show.tmdb_id)
        show_files = self._show_files(show_key)
        return show.upsert_and_set_update_at(source, existing_show, show_files)

    def _merge_and_upsert_season(
        self,
        season: Season,
        show: Show,
        existing_season: Season | None,
        show_key: str,
        tmdb_media_type: Literal["movie", "tv"],
    ) -> Season:
        season = self.tmdb.tmdb_link_season(
            season,
            show.tmdb_id,
            season.season_number,
            tmdb_media_type,
        )
        season_files = self._season_files(season.key, show_key)
        return season.upsert_and_set_update_at(show, existing_season, season_files)

    def _merge_and_upsert_episode(
        self,
        episode: Episode,
        season: Season,
        existing_episode: Episode | None,
        show_key: str,
        tmdb_media_type: Literal["movie", "tv"],
    ) -> Episode:
        episode = self.tmdb.tmdb_link_episode(
            episode,
            season.show.tmdb_id,
            season.season_number,
            episode.episode_number,
            tmdb_media_type,
        )
        episode_files = self._episode_files(episode.key, season.key, show_key)
        return episode.upsert_and_set_update_at(season, existing_episode, episode_files)

    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        raise NotImplementedError

    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        raise NotImplementedError

    def tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:  # noqa: ARG002
        return "tv"

    _tmdb_id: int | None | Sentinel = _UNRESOLVED

    def _existing_show(self, show_key: str) -> Show | None:
        """Return a stored `Show` for `show_key`, preferring one with a `tmdb_id`.

        A plugin can hold the same `show_key` under more than one `Source`, so
        there can be several copies of the same title. They all resolve to the
        same TMDB entry, which is the only thing the caller reads.
        """
        shows = self._preload_show(show_key).all()
        if not shows:
            return None
        return next((show for show in shows if show.tmdb_id), shows[0])

    def _cached_tmdb_id(self, show_key: str) -> int | None:
        """Resolve the TMDB id once for the show the instance is working on.

        Every file listing resolves the id, so without caching a show with many
        episodes repeats the same lookup for each of them. The value is dropped
        by `_reset_show_state` when the instance moves to another show, so it is
        held for one show rather than kept per show key.
        """
        if isinstance(self._tmdb_id, Sentinel):
            self._tmdb_id = self._fetch_tmdb_id(
                show_key,
                self._existing_show(show_key),
            )
        return self._tmdb_id

    def _tmdb_show_file(self, show_key: str) -> ShowDetail | MovieDetails | None:
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        return self.tmdb.show_detail_file(tmdb_id)

    def _tmdb_season_file(
        self,
        season_key: str,
        show_key: str,
    ) -> SeasonDetail | MovieDetails | None:
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
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
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
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
