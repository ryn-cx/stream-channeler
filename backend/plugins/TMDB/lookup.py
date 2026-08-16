# TODO: Validate
from collections.abc import Sequence
from datetime import timedelta
from typing import overload

from tminidb.movie_details.models import MovieDetailsModel
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode
from tminidb.tv_series_details.models import Season as TvSeriesSeason

from app.files.models import File
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


# TODO: Validate
def _found_something(search_file: MovieSearch | TvSearch | MultiSearch) -> bool:
    """Report whether a search came back with anything at all.

    A search TMDB has no answer for is stored empty, and an empty file has no
    results to read out of it.
    """
    if not search_file.database_record.content:
        return False
    return bool(search_file.parsed().results)


# TODO: Validate
class LookupMixin(FileMixin, register=False):
    # TODO: Validate
    @overload
    def auto_updating_search_media(
        self,
        media_type: None,
        query: str,
        year: int | None = None,
    ) -> MultiSearch: ...
    # TODO: Validate
    @overload
    def auto_updating_search_media(
        self,
        media_type: MediaType,
        query: str,
        year: int | None = None,
    ) -> MovieSearch | TvSearch: ...
    # TODO: Validate
    def auto_updating_search_media(
        self,
        media_type: MediaType | None,
        query: str,
        year: int | None = None,
    ) -> MovieSearch | TvSearch | MultiSearch:
        """Return what TMDB answers a name with, downloading it when it is stale.

        A search narrowed to a year that comes back with nothing is asked again
        without one. The year a website carries is the year the title turned up
        there, which for anything licensed from somewhere else is not the year
        TMDB files it under, and a title TMDB is holding is better found under no
        year than not found at all. The year is asked with first all the same,
        since it is what tells two titles of the same name apart.
        """
        search_file = self._searched(media_type, query, year)
        if year is None or _found_something(search_file):
            return search_file
        return self._searched(media_type, query, None)

    # TODO: Validate
    def _searched(
        self,
        media_type: MediaType | None,
        query: str,
        year: int | None,
    ) -> MovieSearch | TvSearch | MultiSearch:
        """Return the search file for one name, downloading it when it is stale."""
        search_file: MovieSearch | TvSearch | MultiSearch
        if media_type == MediaType.movie:
            search_file = self.movie_search_file(query, year)
        elif media_type == MediaType.tv:
            search_file = self.tv_search_file(query, year)
        else:
            search_file = self.multi_search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        return search_file

    # TODO: Validate
    def auto_updating_watch_providers(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        providers_file = self.watch_providers_file(media_type, tmdb_id)
        providers_file.download_if_outdated(tz_datetime.now() - _MEDIA_INFO_MAX_AGE)
        return providers_file

    # TODO: Validate
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

    # TODO: Validate
    def movie_detail(self, tmdb_id: int) -> MovieDetailsModel | None:
        """Return a film's details, downloading them if needed.

        A film is reached by whatever is linked to it as much as by this
        plugin's own media, and nothing else fetches the file on its behalf, so
        it cannot be assumed to be stored already.
        """
        detail_file = self.media_detail_file(MediaType.movie, tmdb_id)
        detail_file.download_if_outdated()
        if not detail_file.database_record.content:
            return None
        return detail_file.parsed()

    # TODO: Validate
    def preload_episode_translations(
        self,
        numberings: Sequence[tuple[int, int, int]],
    ) -> Sequence[File]:
        """Read the rows holding every named episode's translations, in one query.

        Whatever matches episodes by name reads the translations of every episode
        of a title in turn, and a file reached for on its own is a row read on its
        own. Reading them together leaves each of those reaches finding its row
        already in the session.

        The rows are returned so that whatever asked for them can hold on to them
        for as long as it is reading: the session keeps its records weakly, and a
        row nothing holds is dropped and read again.
        """
        return self._get_files_by_keys(
            [
                self.episode_translations_file(
                    tmdb_id,
                    season_number,
                    episode_number,
                ).file_key()
                for tmdb_id, season_number, episode_number in numberings
            ],
        )

    # TODO: Validate
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

    # TODO: Validate
    def alternate_episode_numbers(self, tmdb_id: int) -> dict[int, frozenset[int]]:
        """Return every number each episode of a title carries in some other order.

        TMDB keeps the other ways of ordering a title - the DVD order, the story
        order, an absolute count of the whole run - beside the title's own, and
        the same episode is numbered differently in each of them. A website that
        follows one of those numbers an episode by where that order puts it, so
        the number it wrote down matches none of the title's own and the episode
        is only ever recognised by reading the orders as well.

        Every order is read rather than the chosen one, since the order a
        website follows is not the order the title is stored in and nothing says
        which of them it is. The numbers are keyed by TMDB's own episode id,
        which is what the episode is the same episode by whichever order it is
        read in.

        A title TMDB holds no orders for, and an order stored empty, both read as
        nothing rather than raising: an order is something a title may simply not
        have.
        """
        groups_file = self.episode_groups_file(tmdb_id)
        groups_file.download_if_outdated()
        if not groups_file.database_record.content:
            return {}

        numbers: dict[int, set[int]] = {}
        for option in groups_file.parsed().results:
            detail_file = self.episode_group_detail_file(option.id)
            detail_file.download_if_outdated()
            if not detail_file.database_record.content:
                continue
            for group in detail_file.parsed().groups:
                for number, episode in enumerate(group.episodes, start=1):
                    numbers.setdefault(episode.id, set()).add(number)
        return {
            episode_id: frozenset(episode_numbers)
            for episode_id, episode_numbers in numbers.items()
        }

    # TODO: Validate
    def show_seasons(self, tmdb_id: int) -> Sequence[TvSeriesSeason]:
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

    # TODO: Validate
    def season_episodes(
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

    # TODO: Validate
    def has_season(self, tmdb_id: int, season_number: int) -> bool:
        return any(
            season.season_number == season_number
            for season in self.show_seasons(tmdb_id)
        )

    # TODO: Validate
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
        return any(season.id == season_tmdb_id for season in self.show_seasons(tmdb_id))

    # TODO: Validate
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
            for season in self.show_seasons(tmdb_id)
            for episode in self.season_episodes(tmdb_id, season.season_number)
        )

    # TODO: Validate
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
            for episode in self.season_episodes(tmdb_id, season_number)
        )
