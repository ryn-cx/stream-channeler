# TODO: Validate
from collections.abc import Sequence
from datetime import timedelta

from tminidb.movie_details.models import MovieDetailsModel
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode
from tminidb.tv_series_details.models import Season as TvSeriesSeason

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.TMDB.files import (
    FileMixin,
    MovieDetails,
    MovieSearch,
    MovieWatchProviders,
    MultiSearch,
    TvSearch,
    TvSeriesDetails,
    TvWatchProviders,
)

_SEARCH_MAX_AGE = timedelta(days=7)


_MEDIA_INFO_MAX_AGE = timedelta(days=7)


class LookupMixin(FileMixin, register=False):
    def auto_updating_search_media(
        self,
        media_type: MediaType | None,
        query: str,
        year: int | None = None,
    ) -> MovieSearch | TvSearch | MultiSearch:
        search_file: MovieSearch | TvSearch | MultiSearch
        if media_type == MediaType.movie:
            search_file = self.movie_search_file(query, year)
        elif media_type == MediaType.tv:
            search_file = self.tv_search_file(query, year)
        else:
            search_file = self.multi_search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        return search_file

    def auto_updating_watch_providers(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        providers_file = self.watch_providers_file(media_type, tmdb_id)
        providers_file.download_if_outdated(tz_datetime.now() - _MEDIA_INFO_MAX_AGE)
        return providers_file

    def auto_updating_media_detail(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails:
        """Return the detail file for a title, downloading it when needed.

        A title can be looked up without ever having been imported, and a show
        that was imported stores its details under `ShowDetail` instead, so the
        file this reads cannot be assumed to exist.
        """
        detail_file = self.media_detail_file(media_type, tmdb_id)
        detail_file.download_if_outdated(tz_datetime.now() - _MEDIA_INFO_MAX_AGE)
        return detail_file

    def _movie_detail(self, tmdb_id: int) -> MovieDetailsModel | None:
        return self.media_detail_file(MediaType.movie, tmdb_id).parsed()

    def translated_episode_names(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> Sequence[str]:
        """Return every language's name for one episode of a title.

        An episode's translations are the one thing about a TMDB episode that is
        not stored alongside it, so whatever matches an episode by name reads
        them through here. An episode TMDB has no translations for is stored
        empty and has no names to give.
        """
        translations_file = self.episode_translations_file(
            tmdb_id,
            season_number,
            episode_number,
        )
        translations_file.download_if_outdated()
        if not translations_file.database_record.content:
            return []
        return [
            translation.data.name
            for translation in translations_file.parsed().translations
            if translation.data.name
        ]

    def _show_seasons(self, tmdb_id: int) -> Sequence[TvSeriesSeason]:
        """Return the seasons of a title, downloading the title if needed.

        A title is read by whatever is linked to it as well as by this plugin's
        own media, and the two do not have to have been imported, so the file the
        seasons are read from cannot be assumed to be stored already.
        """
        show_file = self.show_detail_file(tmdb_id)
        show_file.download_if_outdated()
        if not show_file.database_record.content:
            return []
        return show_file.parsed().seasons

    def _season_episodes(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> Sequence[TvSeasonEpisode]:
        """Return the episodes of one season of a title, downloading it if needed.

        A title's seasons are downloaded along with it when this plugin imports
        the title as its own media, but linking and lookups reach for the seasons
        of titles it never imported, so a season file cannot be assumed to be
        stored already. A season TMDB does not have is stored empty and has no
        episodes to give.
        """
        season_file = self.season_detail_file(tmdb_id, season_number)
        season_file.download_if_outdated()
        if not season_file.database_record.content:
            return []
        return season_file.parsed().episodes

    def has_season(self, tmdb_id: int, season_number: int) -> bool:
        return any(
            season.season_number == season_number
            for season in self._show_seasons(tmdb_id)
        )

    def has_season_id(
        self,
        media_type: MediaType,
        tmdb_id: int,
        season_tmdb_id: int,
    ) -> bool:
        """Report whether a title has a season TMDB issued `season_tmdb_id` for.

        TMDB numbers a season within its title but gives it an id of its own, and
        an identifier carries the id rather than the number. A film has no
        seasons, so the single season it is stored as is the film itself.
        """
        if media_type == MediaType.movie:
            return season_tmdb_id == tmdb_id
        return any(
            season.id == season_tmdb_id for season in self._show_seasons(tmdb_id)
        )

    def has_episode_id(
        self,
        media_type: MediaType,
        tmdb_id: int,
        episode_tmdb_id: int,
    ) -> bool:
        """Report whether a title has an episode TMDB issued `episode_tmdb_id` for.

        Every season of the title is read, since an id says nothing about which
        season TMDB files it under. A film has no episodes, so the single episode
        it is stored as is the film itself.
        """
        if media_type == MediaType.movie:
            return episode_tmdb_id == tmdb_id
        return any(
            episode.id == episode_tmdb_id
            for season in self._show_seasons(tmdb_id)
            for episode in self._season_episodes(tmdb_id, season.season_number)
        )

    def has_episode(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> bool:
        if not self.has_season(tmdb_id, season_number):
            return False
        return any(
            episode.episode_number == episode_number
            for episode in self._season_episodes(tmdb_id, season_number)
        )
