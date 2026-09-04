# TODO: Validate
"""Everything the TMDB plugin does that is the same for a series and a film.

TMDB is a plugin like any other: it has a `Source`, and it writes its own
`Show`, `Season` and `Episode` rows through the same upsert every website's
plugin uses. What is different is what those rows are. TMDB is the record of
what a title is rather than a website carrying it, so its rows are the
canonical rows themselves and point at nothing, which is what every other
plugin's non-canonical row points at instead. Nothing can be watched on TMDB,
so its records are left out wherever media is being chosen to play.

A title is read again on a timer, and reading one in full is a file per season
whether anything moved or not. What TMDB's changes endpoints answer is which
records moved, so a read starts by asking that and goes no further than the
records named.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from itertools import pairwise
from typing import Any, ClassVar, overload, override

from sqlmodel import col, select
from tminidb.movie.details.models import MovieDetailsModel
from tminidb.search.multi.models import Result as MultiResult
from tminidb.search.multi.models import SearchMultiModel
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_series.details.models import TvSeriesDetailsModel

from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import chosen_group_id
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesTranslations,
    MoviesWatchProviders,
    ProvidersFile,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVEpisodeGroupsDetails,
    TVEpisodesDetails,
    TVEpisodesTranslations,
    TVSeasonsChanges,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesChanges,
    TVSeriesDetails,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
    TVSeriesWatchProviders,
)
from plugins.TMDB.keys import (
    get_media_type_and_tmdb_id,
    parse_season_key,
)
from plugins.TMDB.utils import (
    SeasonInfo,
    backdrop_image_url,
    decode_cursor,
    encode_cursor,
    found_something,
    media_identifier,
    parse_media_identifier,
    get_media_plugin,
    poster_image_url,
    provider_names,
    release_year,
    title_url_regex,
    watch_provider_items,
)
from plugins.utils.abstract_plugin import (
    PluginMediaInfo,
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin_v3.base import BasePlugin
from plugins.utils.base_plugin_v3.files import (
    COMPLETED_STATUS,
    BaseFile,
)


# TODO: Validate
def media_url(media_type: str, tmdb_id: int) -> str:
    """Return the TMDb URL for the movie or tv series."""
    return f"https://www.themoviedb.org/{media_type}/{tmdb_id}"


MOVIE_URL_REGEX = title_url_regex(TMDBMediaType.movie)


TV_URL_REGEX = title_url_regex(TMDBMediaType.tv) + (
    r"(?:\/season\/(?P<season_number>\d+)(?:\/episode\/(?P<episode_number>\d+))?)?"
)


# TODO: Validate
class TMDBShared(BasePlugin):
    """Reads TMDB into records of TMDB's own.

    A season and an episode are keyed by their own TMDB ids, which is what
    names them wherever they are spoken about, while the API is asked for them
    by the numbering they have within the title. The files already downloaded
    are what turn one into the other, so the numbering is read back rather
    than carried around in the key.
    """

    # TODO: Validate
    @staticmethod
    def _watch_providers_due(record: Show) -> bool:
        if record.update_at is None:
            return False
        return record.update_at <= tz_datetime.now()

    @staticmethod
    def _get_date_from_file_name(file_class: type[BaseFile[Any]], stored: File) -> date:
        """Return the date embedded in the `File.name`."""
        identifier = file_class.file_to_unique_identifier(stored)
        return date.fromisoformat(identifier.split("/")[-1])

    # TODO: Validate
    def latest_file_record(
        self,
        file_class: type[BaseFile[Any]],
        file_prefix: str,
    ) -> File | None:
        """Return the newest `File` for a specific file class and prefix."""
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{file_class.class_key()}/{file_prefix}"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self.session.exec(statement).first()

    # TODO: Validate
    def latest_file_date(
        self,
        file_class: type[BaseFile[Any]],
        file_prefix: str,
    ) -> date:
        """Return the date from the newest `File` for a specific file class and prefix."""
        stored = self.latest_file_record(file_class, file_prefix)
        if stored is None:
            return tz_datetime.now().date()
        return self._get_date_from_file_name(file_class, stored)

    # region Files

    # TODO: Validate
    def files_with_prefix(
        self,
        file_class: type[BaseFile[Any]],
        key_prefix: str,
    ) -> Sequence[File]:
        statement = select(File).where(
            File.plugin == self.plugin,
            col(File.key).startswith(f"{file_class.class_key()}/{key_prefix}"),
        )
        return self.session.exec(statement).all()

    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._file(SearchMulti, query, page)

    def search_movie_file(self, query: str, year: int | None = None) -> SearchMovie:
        return self._file(SearchMovie, query, year)

    def search_tv_file(self, query: str, year: int | None = None) -> SearchTV:
        return self._file(SearchTV, query, year)

    def movies_details_file(self, tmdb_id: int) -> MoviesDetails:
        return self._file(MoviesDetails, str(tmdb_id))

    def movies_translations_file(self, tmdb_id: int) -> MoviesTranslations:
        return self._file(MoviesTranslations, str(tmdb_id))

    def tv_series_details_file(self, tmdb_id: int) -> TVSeriesDetails:
        return self._file(TVSeriesDetails, tmdb_id)

    def latest_tv_series_changes_file(self, show_key: str) -> TVSeriesChanges:
        """Return the latest TV Series Changes file for a show.

        If the file does not exist an initial one will be created."""
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        latest = self.latest_file_date(TVSeriesChanges, f"{tmdb_id}/")
        # If the file does not exist an initial file will be downloaded that covers a
        # single day. If the file does exist only the second parameter is used to get it
        # from the database.
        return self._file(TVSeriesChanges, tmdb_id, latest, latest)

    @overload
    def tv_series_changes_file(
        self,
        show_key: str,
        downloaded_to: date,
    ) -> TVSeriesChanges: ...
    @overload
    def tv_series_changes_file(self, show_key: File) -> TVSeriesChanges: ...
    def tv_series_changes_file(
        self,
        show_key: str | File,
        downloaded_to: date | None = None,
    ) -> TVSeriesChanges:
        if isinstance(show_key, File):
            identifier = TVSeriesChanges.file_to_unique_identifier(show_key)
            tmdb_id_str, downloaded_to_str = identifier.split("/")
            tmdb_id = int(tmdb_id_str)
            downloaded_to = date.fromisoformat(downloaded_to_str)
        else:
            _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return self._file(
            TVSeriesChanges,
            tmdb_id,
            self.latest_file_date(TVSeriesChanges, f"{tmdb_id}/"),
            downloaded_to,
        )

    @overload
    def tv_seasons_changes_file(
        self,
        season_key: str,
        changed_on: date,
    ) -> TVSeasonsChanges: ...
    @overload
    def tv_seasons_changes_file(self, season_key: File) -> TVSeasonsChanges: ...
    def tv_seasons_changes_file(
        self,
        season_key: str | File,
        changed_on: date | None = None,
    ) -> TVSeasonsChanges:
        if isinstance(season_key, File):
            identifier = TVSeasonsChanges.file_to_unique_identifier(season_key)
            season_tmdb_id_str, changed_on_str = identifier.split("/")
            season_tmdb_id = int(season_tmdb_id_str)
            changed_on = date.fromisoformat(changed_on_str)
        else:
            _, season_tmdb_id = parse_season_key(season_key)
        return self._file(TVSeasonsChanges, season_tmdb_id, changed_on)

    # TODO: Validate
    def incomplete_tv_seasons_changes_files(
        self,
        season_key: str,
    ) -> list[TVSeasonsChanges]:
        _, season_tmdb_id = parse_season_key(season_key)
        return self.get_incomplete_files(
            file_class=TVSeasonsChanges,
            factory=self.tv_seasons_changes_file,
            key_prefix=f"{season_tmdb_id}/",
        )

    # TODO: Validate
    def incomplete_tv_series_changes_files(
        self,
        show_key: str,
    ) -> list[TVSeriesChanges]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return self.get_incomplete_files(
            file_class=TVSeriesChanges,
            factory=self.tv_series_changes_file,
            key_prefix=f"{tmdb_id}/",
        )

    def tv_series_images_file(self, tmdb_id: int) -> TVSeriesImages:
        return self._file(TVSeriesImages, tmdb_id)

    def tv_series_episode_groups_file(self, tmdb_id: int) -> TVSeriesEpisodeGroups:
        return self._file(TVSeriesEpisodeGroups, tmdb_id)

    def tv_episode_groups_details_file(self, group_id: str) -> TVEpisodeGroupsDetails:
        return self._file(TVEpisodeGroupsDetails, group_id)

    def tv_seasons_details_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._file(TVSeasonsDetails, tmdb_show_id, season_number)

    def tv_episodes_details_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> TVEpisodesDetails:
        return self._file(
            TVEpisodesDetails,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    def tv_episodes_translations_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> TVEpisodesTranslations:
        return self._file(
            TVEpisodesTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    def latest_movies_watch_providers_file(
        self,
        tmdb_id: int,
    ) -> MoviesWatchProviders:
        """Return the latest Movies Watch Providers file for a movie.

        If the file does not exist an initial one will be created."""
        stored = self.latest_file_record(MoviesWatchProviders, f"{tmdb_id}/")
        if stored is None:
            return self.movies_watch_providers_file(tmdb_id, tz_datetime.now().date())
        return self.movies_watch_providers_file(stored)

    @overload
    def movies_watch_providers_file(
        self,
        tmdb_id: int,
        downloaded_at: date,
    ) -> MoviesWatchProviders: ...
    @overload
    def movies_watch_providers_file(self, tmdb_id: File) -> MoviesWatchProviders: ...
    def movies_watch_providers_file(
        self,
        tmdb_id: int | File,
        downloaded_at: date | None = None,
    ) -> MoviesWatchProviders:
        if isinstance(tmdb_id, File):
            identifier = MoviesWatchProviders.file_to_unique_identifier(tmdb_id)
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_id = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(MoviesWatchProviders, tmdb_id, downloaded_at)

    # TODO: Validate
    def latest_tv_series_watch_providers_file(
        self,
        tmdb_id: int,
    ) -> TVSeriesWatchProviders:
        """Return the latest TV Series Watch Providers file for a show.

        If the file does not exist an initial one will be created."""
        # If no file exists yet the date falls back to today, so the file returned is a
        # new one for today. If one does exist the stored file is returned as it is.
        stored = self.latest_file_record(TVSeriesWatchProviders, f"{tmdb_id}/")
        if stored is None:
            return self.tv_series_watch_providers_file(
                tmdb_id=tmdb_id,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_series_watch_providers_file(stored)

    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_id: int,
        downloaded_at: date,
    ) -> TVSeriesWatchProviders: ...
    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_id: File,
    ) -> TVSeriesWatchProviders: ...
    def tv_series_watch_providers_file(
        self,
        tmdb_id: int | File,
        downloaded_at: date | None = None,
    ) -> TVSeriesWatchProviders:
        if isinstance(tmdb_id, File):
            identifier = TVSeriesWatchProviders.file_to_unique_identifier(tmdb_id)
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_id = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(TVSeriesWatchProviders, tmdb_id, downloaded_at)

    # TODO: Validate
    def latest_tv_seasons_watch_providers_file(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        """Return the latest TV Seasons Watch Providers file for a season.

        If the file does not exist an initial one will be created."""
        # If no file exists yet the date falls back to today, so the file returned is a
        # new one for today. If one does exist the stored file is returned as it is.
        stored = self.latest_file_record(
            file_class=TVSeasonsWatchProviders,
            file_prefix=f"{tmdb_id}/{season_number}/",
        )
        if stored is None:
            return self.tv_seasons_watch_providers_file(
                tmdb_id=tmdb_id,
                season_number=season_number,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_seasons_watch_providers_file(stored)

    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_id: int,
        season_number: int,
        downloaded_at: date,
    ) -> TVSeasonsWatchProviders: ...
    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_id: File,
    ) -> TVSeasonsWatchProviders: ...
    def tv_seasons_watch_providers_file(
        self,
        tmdb_id: int | File,
        season_number: int | None = None,
        downloaded_at: date | None = None,
    ) -> TVSeasonsWatchProviders:
        if isinstance(tmdb_id, File):
            identifier = TVSeasonsWatchProviders.file_to_unique_identifier(tmdb_id)
            tmdb_id_str, season_number_str, downloaded_at_str = identifier.split("/")
            tmdb_id = int(tmdb_id_str)
            season_number = int(season_number_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(
            TVSeasonsWatchProviders,
            tmdb_id,
            season_number,
            downloaded_at,
        )

    # TODO: Validate
    def incomplete_tv_series_watch_providers_files(
        self,
        tmdb_id: int,
    ) -> list[TVSeriesWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeriesWatchProviders,
            factory=self.tv_series_watch_providers_file,
            key_prefix=f"{tmdb_id}/",
        )

    def incomplete_movies_watch_providers_files(
        self,
        tmdb_id: int,
    ) -> list[MoviesWatchProviders]:
        return self.get_incomplete_files(
            file_class=MoviesWatchProviders,
            factory=self.movies_watch_providers_file,
            key_prefix=f"{tmdb_id}/",
        )

    def incomplete_tv_seasons_watch_providers_files(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> list[TVSeasonsWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeasonsWatchProviders,
            factory=self.tv_seasons_watch_providers_file,
            key_prefix=f"{tmdb_id}/{season_number}/",
        )

    @overload
    def search_for_title(
        self,
        media_type: None,
        query: str,
        year: int | None = None,
    ) -> SearchMulti: ...
    @overload
    def search_for_title(
        self,
        media_type: TMDBMediaType,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV: ...
    def search_for_title(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        """Search for a title.

        If no initial match is found, the search is repeated without the year because
        the year is not always reliable."""
        search_file = self.fetch_search_file(media_type, query, year)
        if year is None or found_something(search_file):
            return search_file
        return self.fetch_search_file(media_type, query, None)

    def fetch_search_file(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        year: int | None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        """Fetch the search file from TMDB."""
        search_file: SearchMovie | SearchTV | SearchMulti
        if media_type == TMDBMediaType.movie:
            search_file = self.search_movie_file(query, year)
        elif media_type == TMDBMediaType.tv:
            search_file = self.search_tv_file(query, year)
        else:
            search_file = self.search_multi_file(query)
        search_file.download_if_outdated()
        return search_file

    # TODO: Validate
    def first_search_result(
        self,
        name: str,
        media_type: TMDBMediaType | None,
        year: int | None,
    ) -> tuple[TMDBMediaType, int] | None:
        """Return which half the first title TMDB returns is from, and its id."""
        if media_type is not None:
            results = self.search_for_title(media_type, name, year).parsed().results
            return (media_type, results[0].id) if results else None

        # A search of both halves also returns people, who are no title and are
        # passed over rather than taken as the first result.
        for result in self.search_for_title(None, name, year).parsed().results:
            # Which half of the catalogue a search of both says a result came
            # from. A multi search also returns people, who are no title and
            # cannot be imported.
            half = {"movie": TMDBMediaType.movie, "tv": TMDBMediaType.tv}.get(
                result.media_type,
            )
            if half is not None:
                return half, result.id
        return None

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
            file_keys=[
                self.tv_episodes_translations_file(
                    tmdb_show_id=tmdb_id,
                    season_number=season_number,
                    episode_number=episode_number,
                ).file_key()
                for tmdb_id, season_number, episode_number in numberings
            ],
        )

    # TODO: Validate
    def preload_movie_translations(self, tmdb_ids: Sequence[int]) -> Sequence[File]:
        """Read the rows holding every named film's translations, in one query.

        The same reason the episodes of a title are read together: a film reached
        for on its own is a row read on its own, and whatever matches films by
        name reads them one after another.
        """
        return self._get_files_by_keys(
            [self.movies_translations_file(tmdb_id).file_key() for tmdb_id in tmdb_ids],
        )

    # endregion

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
        them through here.
        """
        translations = self.tv_episodes_translations_file(
            tmdb_show_id=tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
        ).parsed()
        return [
            translation.data.name
            for translation in translations.translations
            if translation.data.name
        ]

    # TODO: Validate
    def translated_movie_names(self, tmdb_id: int) -> Sequence[str]:
        """Return every language's title for one film.

        A film's translations are not stored alongside it, the same way an
        episode's are not, so whatever matches a film by name reads them through
        here.
        """
        translations = self.movies_translations_file(tmdb_id).parsed()
        return [
            translation.data.title
            for translation in translations.translations
            if translation.data and translation.data.title
        ]

    # TODO: Validate
    def alternate_episode_numbers(
        self,
        tmdb_id: int,
    ) -> dict[int, dict[int, frozenset[str]]]:
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
        """
        groups = self.tv_series_episode_groups_file(tmdb_id).parsed()

        numbers: dict[int, dict[int, set[str]]] = {}
        for option in groups.results:
            detail = self.tv_episode_groups_details_file(option.id).parsed()
            for group in detail.groups:
                for number, episode in enumerate(group.episodes, start=1):
                    order_names = numbers.setdefault(episode.id, {}).setdefault(
                        number,
                        set(),
                    )
                    order_names.add(detail.name)
        return {
            episode_id: {
                number: frozenset(order_names)
                for number, order_names in episode_numbers.items()
            }
            for episode_id, episode_numbers in numbers.items()
        }

    # TODO: Validate
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        media_type, tmdb_id = parse_media_identifier(media_identifier)
        detail_file: MoviesDetails | TVSeriesDetails
        providers_file: MoviesWatchProviders | TVSeriesWatchProviders
        if media_type == TMDBMediaType.movie:
            detail_file = self.movies_details_file(tmdb_id)
            providers_file = self.latest_movies_watch_providers_file(tmdb_id)
        else:
            detail_file = self.tv_series_details_file(tmdb_id)
            providers_file = self.latest_tv_series_watch_providers_file(tmdb_id)
        providers = providers_file.parsed()
        # Which of the two shapes the detail is has to be read off the file rather
        # than the parsed model, because a model whose module was reloaded after a
        # schema change is no longer an instance of the class imported here.
        detail: MovieDetailsModel | TvSeriesDetailsModel
        # A title with no poster of its own can still be shown by a poster one of
        # its seasons carries.
        season_poster_path: str | None
        if isinstance(detail_file, MoviesDetails):
            detail = detail_file.parsed()
            title = detail.title
            year = release_year(detail.release_date)
            end_year = None
            number_of_seasons = None
            number_of_episodes = None
            runtime = detail.runtime
            season_poster_path = None
        else:
            detail = detail_file.parsed()
            title = detail.name
            year = release_year(detail.first_air_date)
            end_year = release_year(detail.last_air_date)
            number_of_seasons = detail.number_of_seasons
            number_of_episodes = detail.number_of_episodes
            runtime = None
            season_poster_path = next(
                (season.poster_path for season in detail.seasons if season.poster_path),
                None,
            )

        # Either image stands in for the other when its own path is missing, sized
        # for the slot it fills rather than the slot it came from.
        poster_path = detail.poster_path or season_poster_path
        backdrop_path = detail.backdrop_path
        return PluginMediaInfo(
            title=title,
            media_type={TMDBMediaType.movie: "Movie", TMDBMediaType.tv: "TV Show"}[
                media_type
            ],
            tagline=detail.tagline or None,
            overview=detail.overview or None,
            poster_url=poster_image_url(poster_path or backdrop_path),
            backdrop_url=backdrop_image_url(backdrop_path or poster_path),
            year=year,
            end_year=end_year,
            status=detail.status,
            rating=detail.vote_average,
            vote_count=detail.vote_count,
            number_of_seasons=number_of_seasons,
            number_of_episodes=number_of_episodes,
            runtime=runtime,
            genres=[genre.name for genre in detail.genres],
            providers=watch_provider_items(providers, title),
        )

    # A multi search also returns people, who cannot be added to a channel.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "movie": "Movie",
        "tv": "TV Show",
    }

    # TODO: Validate
    @classmethod
    def search_page_size(cls) -> int:
        return 20

    # TODO: Validate
    def in_app_search(
        self,
        query: str,
        cursor: str | None = None,
    ) -> PluginSearchResults:
        """Search every title TMDB knows about, whatever it streams on.

        A result's URL is the title's own TMDB page rather than a stream, since
        `import_url` reads that page to find where the title can be watched.
        """
        page, offset = decode_cursor(cursor)
        results: list[PluginSearchResult] = []
        next_cursor: str | None = None

        while len(results) < self.search_page_size():
            parsed = self._multi_search_page(query, page)
            matches = [
                self._search_result(result)
                for result in parsed.results
                if result.media_type in self._SEARCH_MEDIA_TYPES
            ][offset:]

            wanted = self.search_page_size() - len(results)
            results.extend(matches[:wanted])
            if len(matches) > wanted:
                next_cursor = encode_cursor(page, offset + wanted)
                break

            page += 1
            offset = 0
            if page > parsed.total_pages:
                next_cursor = None
                break
            next_cursor = encode_cursor(page, 0)

        return PluginSearchResults(results=results, next_cursor=next_cursor)

    # TODO: Validate
    def _multi_search_page(self, query: str, page: int) -> SearchMultiModel:
        return self.search_multi_file(query, page).parsed()

    # TODO: Validate
    def _search_result(self, result: MultiResult) -> PluginSearchResult:
        # A movie carries its title and release date, a show its name and first
        # air date, and a multi search returns the two mixed together.
        title: str | None
        media_type: TMDBMediaType
        if result.media_type == "movie":
            media_type = TMDBMediaType.movie
            title = result.title or result.original_title
            year = release_year(result.release_date)
        else:
            media_type = TMDBMediaType.tv
            title = result.name or result.original_name
            year = release_year(result.first_air_date)

        if not title:
            msg = f"TMDB {result.media_type} {result.id} has no title"
            raise ValueError(msg)

        return PluginSearchResult(
            title=title,
            url=media_url(media_type, result.id),
            year=year,
            image_url=poster_image_url(result.poster_path)
            or backdrop_image_url(result.backdrop_path),
            media_type=self._SEARCH_MEDIA_TYPES[media_type],
            media_identifier=media_identifier(media_type, result.id),
        )

    # TODO: Validate
    def _chosen_episode_group(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> TvEpisodeGroupDetailsModel | None:
        show = Show.get(self.session, self.source, show_key)
        if show and (group_id := chosen_group_id(show.extra)):
            return self.tv_episode_groups_details_file(group_id).parsed(update_at)
        return None

    def chosen_seasons(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[SeasonInfo]:
        """Return the seasons for the show.

        If the show uses an episode_group the the seasons will be based on the contents
        of TVEpisodeGroupsDetails.

        If the show does not use an episode_group the seasons will be based on the
        contents of TVSeriesDetails.
        """

        _, tmdb_id = get_media_type_and_tmdb_id(show_key)

        if group := self._chosen_episode_group(show_key, update_at):
            return [
                SeasonInfo.from_episode_group(order, entry)
                for order, entry in enumerate(group.groups)
            ]

        return [
            SeasonInfo.from_season_details(
                self.tv_seasons_details_file(
                    tmdb_show_id=tmdb_id,
                    season_number=season.season_number,
                ).parsed(update_at),
            )
            for season in self.tv_series_details_file(tmdb_id).parsed(update_at).seasons
        ]

    def _native_season_number(self, season_key: str, show_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, season_tmdb_id = parse_season_key(season_key)
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        for season in self.tv_series_details_file(tmdb_id).parsed().seasons:
            if season.id == season_tmdb_id:
                return season.season_number
        message = f"{show_key} has no season {season_key}"
        raise ValueError(message)

    def _process_watch_providers(
        self,
        show_key: str,
        files: Sequence[ProvidersFile],
    ) -> None:
        """Process all of the supplied WatchProvider files for a single show."""
        for old_watch_providers_files, new_watch_providers_file in pairwise(files):
            changed_watch_providers = provider_names(
                file=old_watch_providers_files,
            ) ^ provider_names(
                file=new_watch_providers_file,
            )
            for changed_watch_provider in changed_watch_providers:
                self._process_changed_provider(
                    show_key=show_key,
                    changed_provider=changed_watch_provider,
                    update_at=new_watch_providers_file.data_timestamp(),
                )
            record = old_watch_providers_files.database_record
            record.status = COMPLETED_STATUS
            record.update_at = None

    def _process_changed_provider(
        self,
        show_key: str,
        changed_provider: str,
        update_at: datetime,
    ) -> None:
        """Process a single changed provider.

        Sets the show.updated_at and season.updated_at values."""
        plugin = get_media_plugin(changed_provider)
        if plugin := get_media_plugin(changed_provider):
            canonical_show = Show.get_one(self.session, self.source, show_key)
            for canonical_link in canonical_show.non_canonical_show_links:
                if (
                    canonical_link.non_canonical_show.source.plugin.key
                    == plugin.plugin_name()
                ):
                    # Watch provider status changing warrants a complete updates of both
                    # the show and season files for simplicity.
                    canonical_link.non_canonical_show.set_update_at(update_at)
                    for season in canonical_link.non_canonical_show.active_children:
                        season.set_update_at(update_at)

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "TMDB"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "themoviedb.org"
