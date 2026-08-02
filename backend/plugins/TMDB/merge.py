# TODO: Validate
from collections.abc import Sequence
from typing import Literal, Protocol

from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.TMDB.files import (
    air_datetime,
    backdrop_image_url,
    duration_seconds,
    poster_image_url,
    still_image_url,
)
from plugins.TMDB.lookup import LookupMixin


class _Named(Protocol):
    name: str


def _plaintext(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def _find_by_name[NamedType: _Named](
    candidates: Sequence[NamedType],
    name: str | None,
) -> NamedType | None:
    if not name:
        return None

    target = _plaintext(name)
    matches = [
        candidate for candidate in candidates if _plaintext(candidate.name) == target
    ]
    return matches[0] if len(matches) == 1 else None


class MergeMixin(LookupMixin, register=False):
    def tmdb_merge_show(
        self,
        show: Show,
        tmdb_id: int | None,
        media_type: Literal["movie", "tv"] = "tv",
    ) -> Show:
        """Take a Show and add missing values from TMDB."""
        show.tmdb_id = show.tmdb_id or tmdb_id
        if not show.tmdb_id:
            return show

        if media_type == "movie":
            movie = self._movie_detail(show.tmdb_id)
            if movie:
                show.name = show.name or movie.title
                show.description = show.description or movie.overview
                show.image_url = (
                    show.image_url
                    or backdrop_image_url(movie.backdrop_path)
                    or poster_image_url(movie.poster_path)
                )
            return show

        show_detail = self.show_detail_file(show.tmdb_id).parsed()
        show.name = show.name or show_detail.name
        show.description = show.description or show_detail.overview
        show.image_url = (
            show.image_url
            or backdrop_image_url(show_detail.backdrop_path)
            or poster_image_url(show_detail.poster_path)
        )
        return show

    def tmdb_merge_season(
        self,
        season: Season,
        tmdb_id: int | None,
        season_number: int | None,
        media_type: Literal["movie", "tv"],
    ) -> Season:
        """Take a Season and add missing values from TMDB."""
        if not tmdb_id:
            return season

        if media_type == "movie":
            movie = self._movie_detail(tmdb_id)
            if movie:
                season.name = season.name or movie.title
                season.image_url = season.image_url or poster_image_url(
                    movie.poster_path,
                )
                season.tmdb_id = season.tmdb_id or movie.id
            return season

        seasons = self.show_detail_file(tmdb_id).parsed().seasons
        season_detail = next(
            (
                candidate
                for candidate in seasons
                if candidate.season_number == season_number
            ),
            None,
        )
        if season_detail is None:
            season_detail = _find_by_name(seasons, season.name)
        if season_detail:
            season.name = season.name or season_detail.name
            season.image_url = season.image_url or poster_image_url(
                season_detail.poster_path,
            )
            season.tmdb_id = season.tmdb_id or season_detail.id
        return season

    def tmdb_merge_episode(
        self,
        episode: Episode,
        tmdb_id: int | None,
        season_number: int | None,
        episode_number: int | None,
        media_type: Literal["movie", "tv"] = "tv",
    ) -> Episode:
        """Take an Episode and add missing values from TMDB."""
        if not tmdb_id:
            return episode

        if media_type == "movie":
            if movie := self._movie_detail(tmdb_id):
                movie_release = air_datetime(movie.release_date)
                episode.name = episode.name or movie.title
                episode.description = episode.description or movie.overview
                episode.image_url = episode.image_url or backdrop_image_url(
                    movie.backdrop_path,
                )
                episode.duration = episode.duration or duration_seconds(movie.runtime)
                episode.release_date = episode.release_date or movie_release
                episode.air_date = episode.air_date or movie_release
                episode.tmdb_id = episode.tmdb_id or movie.id
                episode.episode_identifier = f"TMDB {movie.id}"
            return episode

        episode_detail = self._episode_detail(
            tmdb_id,
            season_number,
            episode_number,
            episode.name,
        )
        if episode_detail:
            episode.name = episode.name or episode_detail.name
            episode.description = episode.description or episode_detail.overview
            episode.image_url = episode.image_url or still_image_url(
                episode_detail.still_path,
            )
            episode.duration = episode.duration or duration_seconds(
                episode_detail.runtime,
            )
            air = air_datetime(episode_detail.air_date)
            episode.release_date = episode.release_date or air
            episode.air_date = episode.air_date or air
            episode.tmdb_id = episode.tmdb_id or episode_detail.id
            episode.episode_identifier = f"TMDB {episode_detail.id}"
        return episode

    def _episode_detail(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        episodes = self._all_episodes(tmdb_id)

        if episode_detail := _find_by_name(episodes, episode_name):
            return episode_detail

        return self._episode_by_number(tmdb_id, season_number, episode_number)

    def _episode_by_number(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        if not season_number or not episode_number:
            return None
        if not self.has_season(tmdb_id, season_number):
            return None

        episodes = self.season_detail_file(tmdb_id, season_number).parsed().episodes
        return next(
            (
                candidate
                for candidate in episodes
                if candidate.episode_number == episode_number
            ),
            None,
        )

    _all_episodes_cache: dict[int, list[TvSeasonEpisode]]

    def _all_episodes(self, tmdb_id: int) -> list[TvSeasonEpisode]:
        """Return every episode of a show, read once for the life of the plugin.

        Every episode of a show looks its name up in the same list, so without
        caching a show re-reads all of its season files once per episode.
        """
        if not hasattr(self, "_all_episodes_cache"):
            self._all_episodes_cache = {}
        if tmdb_id in self._all_episodes_cache:
            return self._all_episodes_cache[tmdb_id]

        episodes: list[TvSeasonEpisode] = []
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            season_detail = self.season_detail_file(
                tmdb_id,
                season.season_number,
            ).parsed()
            episodes.extend(season_detail.episodes)
        self._all_episodes_cache[tmdb_id] = episodes
        return episodes
