# TODO: Validate
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Literal, overload, override

from tminidb.movie_details.models import MovieDetailsModel
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.TMDB.files import (
    LOOKUP_ONLY_MESSAGE,
    FileMixin,
    MovieSearch,
    MovieWatchProviders,
    MultiSearch,
    TvSearch,
    TvWatchProviders,
    air_datetime,
    backdrop_image_url,
    duration_seconds,
    poster_image_url,
    still_image_url,
)

_SEARCH_MAX_AGE = timedelta(days=7)
_MEDIA_INFO_MAX_AGE = timedelta(days=7)


def _plaintext(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


class TMDB(FileMixin, register=True):
    _VERSION = "0.0.1"

    # TMDB Just needs to make a plugin database entry to store files.
    @override
    def initialize_source(self) -> None:
        return

    @overload
    def auto_updating_search_media(
        self,
        media_type: Literal["movie"],
        query: str,
        year: int | None = None,
    ) -> MovieSearch: ...
    @overload
    def auto_updating_search_media(
        self,
        media_type: Literal["tv"],
        query: str,
        year: int | None = None,
    ) -> TvSearch: ...
    @overload
    def auto_updating_search_media(
        self,
        media_type: None,
        query: str,
        year: int | None = None,
    ) -> MultiSearch: ...
    def auto_updating_search_media(
        self,
        media_type: Literal["movie", "tv"] | None,
        query: str,
        year: int | None = None,
    ) -> MovieSearch | TvSearch | MultiSearch:
        search_file: MovieSearch | TvSearch | MultiSearch
        if media_type == "movie":
            search_file = self.movie_search_file(query, year)
        elif media_type == "tv":
            search_file = self.tv_search_file(query, year)
        else:
            search_file = self.multi_search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        return search_file

    @overload
    def auto_updating_watch_providers(
        self,
        media_type: Literal["movie"],
        tmdb_id: int,
    ) -> MovieWatchProviders: ...
    @overload
    def auto_updating_watch_providers(
        self,
        media_type: Literal["tv"],
        tmdb_id: int,
    ) -> TvWatchProviders: ...
    def auto_updating_watch_providers(
        self,
        media_type: Literal["movie", "tv"],
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        providers_file = self.watch_providers_file(media_type, tmdb_id)
        providers_file.download_if_outdated(tz_datetime.now() - _MEDIA_INFO_MAX_AGE)
        return providers_file

    def _movie_detail(self, tmdb_id: int) -> MovieDetailsModel | None:
        return self.media_detail_file("movie", tmdb_id).parsed()

    def has_season(self, tmdb_id: int, season_number: int) -> bool:
        show_detail = self.show_detail_file(tmdb_id).parsed()
        return any(
            season.season_number == season_number for season in show_detail.seasons
        )

    def has_episode(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> bool:
        if not self.has_season(tmdb_id, season_number):
            return False
        season_detail = self.season_detail_file(tmdb_id, season_number).parsed()
        return any(
            episode.episode_number == episode_number
            for episode in season_detail.episodes
        )

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

        if not season_number:
            return season
        season_detail = next(
            (
                candidate
                for candidate in self.show_detail_file(tmdb_id).parsed().seasons
                if candidate.season_number == season_number
            ),
            None,
        )
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
            movie = self._movie_detail(tmdb_id)
            if movie:
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

        if not (season_number and episode_number):
            return episode
        if not self.has_season(tmdb_id, season_number):
            return episode
        episodes = self.season_detail_file(tmdb_id, season_number).parsed().episodes
        episode_detail = next(
            (
                candidate
                for candidate in episodes
                if candidate.episode_number == episode_number
            ),
            None,
        )
        if episode_detail is None:
            episode_detail = self._find_episode_by_name(episodes, episode.name)
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

    def _find_episode_by_name(
        self,
        candidates: list[TvSeasonEpisode],
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        if not episode_name:
            return None
        exact_match = self._find_exact_match(candidates, episode_name)
        if exact_match is not None:
            return exact_match
        return self._find_fuzzy_match(candidates, episode_name)

    @staticmethod
    def _find_exact_match(
        candidates: list[TvSeasonEpisode],
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        matches = [
            candidate for candidate in candidates if candidate.name == episode_name
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _find_fuzzy_match(
        candidates: list[TvSeasonEpisode],
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        target = _plaintext(episode_name)
        matches = [
            candidate
            for candidate in candidates
            if _plaintext(candidate.name) == target
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    @classmethod
    @override
    def _url_regex(cls) -> str:
        return r"(?!)"

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_source(self, source: Source) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_season(self, season: Season) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_episode(self, episode: Episode) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)
