# TODO: Validate

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from itertools import pairwise
from typing import ClassVar, overload, override

from tminidb.movie.details.models import MovieDetailsModel
from tminidb.search.multi.models import Result as MultiResult
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_series.details.models import TvSeriesDetailsModel

from app.canonical_media.tmdb import (
    chosen_group_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.basic_files import BasicFiles
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesWatchProviders,
    ProvidersFile,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVSeriesDetails,
    TVSeriesWatchProviders,
)
from plugins.TMDB.utils import (
    SeasonInfo,
    decode_cursor,
    encode_cursor,
    image_url,
    get_media_plugin,
    parse_media_identifier,
    provider_names,
    release_year,
    thumbnail_url,
    title_url_regex,
    watch_provider_items,
)
from plugins.utils.abstract_plugin import (
    PluginMediaInfo,
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin_v3.files import COMPLETED_STATUS


# TODO: Validate
def media_url(media_type: str, tmdb_media_id: int) -> str:
    """Return the TMDb URL for the movie or tv series."""
    return f"https://www.themoviedb.org/{media_type}/{tmdb_media_id}"


MOVIE_URL_REGEX = title_url_regex(TMDBMediaType.movie)


TV_URL_REGEX = title_url_regex(TMDBMediaType.tv) + (
    r"(?:\/season\/(?P<season_number>\d+)(?:\/episode\/(?P<episode_number>\d+))?)?"
)


# TODO: Validate
class TMDBShared(BasicFiles):
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

    # TODO: Validate
    def first_search_result(
        self,
        name: str,
        media_type: TMDBMediaType | None,
        year: int | None,
    ) -> tuple[TMDBMediaType, int] | None:
        """Return the media_type and the id of the first search result."""
        if media_type:
            results = self._search_for_title(media_type, name, year).parsed().results
            return (media_type, results[0].id) if results else None

        for result in self._search_for_title(None, name, year).parsed().results:
            # SearchMulti returns movies, tv shows, people, collections etc. The results
            # need to be filtered to only movies and tv shows.
            if result.media_type in set(TMDBMediaType):
                return TMDBMediaType(result.media_type), result.id
        return None

    # TODO: Validate
    @overload
    def _search_for_title(
        self,
        media_type: None,
        query: str,
        year: int | None = None,
    ) -> SearchMulti: ...
    # TODO: Validate
    @overload
    def _search_for_title(
        self,
        media_type: TMDBMediaType,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV: ...
    # TODO: Validate
    def _search_for_title(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        """Search for a title.

        If no initial match is found, the search is repeated without the year because
        the year is not always reliable."""
        search_file = self._fetch_search_file(media_type, query, year)
        if search_file.parsed().results or not year:
            return search_file
        return self._fetch_search_file(media_type, query, None)

    # TODO: Validate
    def _fetch_search_file(
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
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        media_type, tmdb_media_id = parse_media_identifier(media_identifier)
        detail_file: MoviesDetails | TVSeriesDetails
        providers_file: MoviesWatchProviders | TVSeriesWatchProviders
        if media_type == TMDBMediaType.movie:
            detail_file = self.movies_details_file(tmdb_media_id)
            providers_file = self.latest_movies_watch_providers_file(tmdb_media_id)
        else:
            detail_file = self.tv_series_details_file(tmdb_media_id)
            providers_file = self.latest_tv_series_watch_providers_file(tmdb_media_id)
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
            poster_url=thumbnail_url(poster_path or backdrop_path),
            backdrop_url=image_url(backdrop_path or poster_path),
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
            parsed = self.search_multi_file(query, page).parsed()
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
    def _search_result(self, result: MultiResult) -> PluginSearchResult:
        """Return a PluginSearchResult from a TMDB search result."""

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
            image_url=thumbnail_url(result.poster_path)
            or image_url(result.backdrop_path),
            media_type=self._SEARCH_MEDIA_TYPES[media_type],
            media_identifier=f"{media_type} {result.id}",
        )

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

        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)

        if group := self._chosen_episode_group(show_key, update_at):
            return [
                SeasonInfo.from_episode_group(order, entry)
                for order, entry in enumerate(group.groups)
            ]

        return [
            SeasonInfo.from_season_details(
                self.tv_seasons_details_file(
                    tmdb_tv_show_id=tmdb_tv_show_id,
                    season_number=season.season_number,
                ).parsed(update_at),
            )
            for season in self.tv_series_details_file(tmdb_tv_show_id)
            .parsed(update_at)
            .seasons
        ]

    def _native_season_number(self, season_key: str, show_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        for season in self.tv_series_details_file(tmdb_tv_show_id).parsed().seasons:
            if season.id == tmdb_tv_season_id:
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
