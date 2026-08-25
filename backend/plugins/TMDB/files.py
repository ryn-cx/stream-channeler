# TODO: Validate
from abc import abstractmethod
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import (
    Any,
    Literal,
    NamedTuple,
    overload,
    override,
)

from pydantic import BaseModel
from sqlmodel import Session, col, select
from tminidb.changes.tv_series import models as tv_series_changes
from tminidb.changes.tv_series.models import Change, TvSeriesChangesModel
from tminidb.details.movie import models as movie_details
from tminidb.details.movie.models import MovieModel
from tminidb.details.tv_episode import models as tv_episode_details
from tminidb.details.tv_episode.models import TvEpisodeModel
from tminidb.details.tv_season import models as tv_season_details
from tminidb.details.tv_season.models import Episode, TvSeasonModel
from tminidb.details.tv_series import models as tv_series_details
from tminidb.details.tv_series.models import TvSeriesModel
from tminidb.search.movie import models as search_movie
from tminidb.search.movie.models import SearchMovieModel
from tminidb.search.multi import models as search_multi
from tminidb.search.multi.models import SearchMultiModel
from tminidb.search.tv import models as search_tv
from tminidb.search.tv.models import SearchTvModel
from tminidb.tv_episode_group import models as tv_episode_group
from tminidb.tv_episode_group.models import Episode as GroupEpisode
from tminidb.tv_episode_group.models import TvEpisodeGroupModel
from tminidb.tv_episode_translations import models as tv_episode_translations
from tminidb.tv_episode_translations.models import TvEpisodeTranslationsModel
from tminidb.tv_series_episode_groups import models as tv_series_episode_groups
from tminidb.tv_series_episode_groups.models import Result as EpisodeGroupSummary
from tminidb.tv_series_episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.watch_providers.movie import models as movie_watch_providers_models
from tminidb.watch_providers.movie.models import MovieWatchProvidersModel
from tminidb.watch_providers.tv_series import models as tv_series_watch_providers_models
from tminidb.watch_providers.tv_series.models import TvSeriesWatchProvidersModel

from app.files.models import File
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB import api
from plugins.TMDB.episode_groups import chosen_group_id
from plugins.TMDB.keys import (
    parse_season_key,
    parse_show_key,
    season_key,
)
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON, HTMLFile
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client

TMDB_DOMAIN = "themoviedb.org"


# TODO: Validate
def title_page_url(media_type: str, tmdb_id: int) -> str:
    """Return the themoviedb.org page a user would visit for a title."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}?language=en-US"


_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
_STILL_BASE_URL = "https://image.tmdb.org/t/p/original"
_LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"
_LATEST_SHOW_CHANGES_DATES = "tmdb_latest_show_changes_dates"


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def poster_image_url(path: str | None) -> str | None:
    return _image_url(_POSTER_BASE_URL, path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url(_BACKDROP_BASE_URL, path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url(_STILL_BASE_URL, path)


# TODO: Validate
def logo_image_url(path: str | None) -> str | None:
    return _image_url(_LOGO_BASE_URL, path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: str | date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, and every date the API answers with arrives as the text
    # TMDB wrote rather than as a date.
    if not air_date:
        return None
    if isinstance(air_date, str):
        air_date = date.fromisoformat(air_date)
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
class _TMDBEndpointFile[T: BaseModel](EndpointJSON[T]):
    """TMDB endpoint file.

    An endpoint is called rather than asked to download and parse, and what it
    answers with is the parsed response itself, so what is stored is that
    response and what is read back is the same object again.
    """

    # TODO: Validate
    @abstractmethod
    def _fetch_json(self) -> dict[str, Any]: ...

    # TODO: Validate
    @abstractmethod
    @override
    def _parse(self, raw: Any) -> T: ...

    # TODO: Validate
    @override
    def _fetch(self) -> T:
        return self._parse(self._fetch_json())

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch_json()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)

    # Occurs when a user puts in a URL for a title TMDB does not have, and when a
    # season or an episode is asked for by a number the title does not run to.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return (
            isinstance(error, api.TMDBHTTPError)
            and error.status_code == HTTPStatus.NOT_FOUND
        )


# TODO: Validate
class MovieDetails(_TMDBEndpointFile[MovieModel]):
    """Movie details file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> MovieModel:
        return movie_details.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.movie_details(int(self.unique_identifier))


# TODO: Validate
class TvSeriesDetails(_TMDBEndpointFile[TvSeriesModel]):
    """TV series details file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeriesModel:
        return tv_series_details.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_series_details(int(self.unique_identifier))


# TODO: Validate
class MovieWatchProviders(_TMDBEndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> MovieWatchProvidersModel:
        return movie_watch_providers_models.model_validate_json(
            raw,
            self.file_key(),
        )

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.movie_watch_providers(int(self.unique_identifier))


# TODO: Validate
class TvWatchProviders(_TMDBEndpointFile[TvSeriesWatchProvidersModel]):
    """TV watch providers file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeriesWatchProvidersModel:
        return tv_series_watch_providers_models.model_validate_json(
            raw,
            self.file_key(),
        )

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_series_watch_providers(int(self.unique_identifier))


# TODO: Validate
class ShowDetail(_TMDBEndpointFile[TvSeriesModel]):
    """Show detail file.

    The seasons and episodes under a title are reached through
    `_season_keys_from_file` and `_episode_keys_from_file`, so this file only
    carries the title itself.
    """

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeriesModel:
        return tv_series_details.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_series_details(int(self.unique_identifier))


# TODO: Validate
class EpisodeGroups(_TMDBEndpointFile[TvSeriesEpisodeGroupsModel]):
    """Every episode order TMDB holds for a title, beside the title's own.

    Only what each order is called and how big it is - the episodes an order
    puts where are `EpisodeGroupDetail`, one file per order, since a title with
    six orders is six files nobody wants downloaded to read a list of names.
    """

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeriesEpisodeGroupsModel:
        return tv_series_episode_groups.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_series_episode_groups(int(self.unique_identifier))


# TODO: Validate
class EpisodeGroupDetail(_TMDBEndpointFile[TvEpisodeGroupModel]):
    """One episode order, and the episodes each of its groups holds.

    Keyed by the order's own id rather than by the title's, because that is what
    TMDB looks it up by and one order belongs to one title anyway. The id is a
    string of TMDB's own making rather than a number, so it is passed along as
    it came rather than as a number.
    """

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvEpisodeGroupModel:
        return tv_episode_group.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_episode_group_details(self.unique_identifier)


# TODO: Validate
class SeasonDetail(_TMDBEndpointFile[TvSeasonModel]):
    """Season detail file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{tmdb_show_id}/{season_number}")

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeasonModel:
        return tv_season_details.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_season_details(
            self.tmdb_show_id,
            self.season_number,
        )


# TODO: Validate
class EpisodeDetail(_TMDBEndpointFile[TvEpisodeModel]):
    """Episode detail file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        self.episode_number = episode_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvEpisodeModel:
        return tv_episode_details.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_episode_details(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class EpisodeTranslations(_TMDBEndpointFile[TvEpisodeTranslationsModel]):
    """Every language's name for a single episode."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        self.episode_number = episode_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvEpisodeTranslationsModel:
        return tv_episode_translations.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.tv_episode_translations(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


CHANGES_OVERLAP = timedelta(days=2)


# TODO: Validate
def change_datetime(changed_at: str) -> datetime:
    return tz_datetime.fromisoformat(changed_at.replace(" UTC", "+00:00"))


# TODO: Validate
class ShowChanges(_TMDBEndpointFile[TvSeriesChangesModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        since: date,
        downloaded_to: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.since = since
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{downloaded_to.isoformat()}",
        )

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TvSeriesChangesModel:
        return tv_series_changes.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        # An end date is asked with as well as a start, because TMDB answers a
        # start on its own with the fortnight after it rather than everything
        # since, and a title left alone for longer than that would have the
        # changes either side of its first fortnight go unread. Asked with both,
        # the endpoint splits the range and merges what each part answers with.
        return api.tv_series_changes(
            self.tmdb_show_id,
            start_date=self.since,
            end_date=tz_datetime.now().date(),
        )

    # TODO: Validate
    def changes(self) -> Sequence[Change]:
        if not self.database_record.content:
            return []
        return self.parsed().changes


# TODO: Validate
class MultiSearch(_TMDBEndpointFile[SearchMultiModel]):
    """Multi search file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        page: int = 1,
    ) -> None:
        self.query = query
        self.page = page
        super().__init__(session, plugin, query if page == 1 else f"{query}/{page}")

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> SearchMultiModel:
        return search_multi.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.search_multi(self.query, page=self.page)


# TODO: Validate
class TitlePage(HTMLFile):
    """The themoviedb.org web page for a single title.

    Downloaded to tell a URL naming a title TMDB holds from one naming nothing,
    which is what a pasted address is checked against.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        media_type: str,
        tmdb_id: int,
    ) -> None:
        self.media_type = media_type
        self.tmdb_id = tmdb_id
        super().__init__(session, plugin, f"{media_type}/{tmdb_id}")

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            url = title_page_url(self.media_type, self.tmdb_id)
            response = get_around_client().get(url, follow_redirects=True)
            if response.status_code == HTTPStatus.NOT_FOUND:
                self.write(None)
                return
            response.raise_for_status()
            self.write(response.text)


# TODO: Validate
class MovieSearch(_TMDBEndpointFile[SearchMovieModel]):
    """Movie search file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> SearchMovieModel:
        return search_movie.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        year = None if self.year is None else str(self.year)
        return api.search_movie(self.query, year=year)


# TODO: Validate
class TvSearch(_TMDBEndpointFile[SearchTvModel]):
    """TV search file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> SearchTvModel:
        return search_tv.model_validate_json(raw, self.file_key())

    # TODO: Validate
    @override
    def _fetch_json(self) -> dict[str, Any]:
        return api.search_tv(self.query, year=self.year)


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    number: int
    entry: Episode | GroupEpisode


# TODO: Validate
class SeasonSource(NamedTuple):
    """One season of a title, however the title is being read.

    The two ways of reading a series - TMDB's own seasons and a chosen episode
    order - answer with different files holding different shapes, and everything
    that writes a season wants the same handful of things out of either. So both
    are read into this and nothing downstream asks which it was.
    """

    key: str
    name: str | None
    season_number: int
    poster_path: str | None
    episodes: list[EpisodeSource]


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    # TODO: Validate
    def multi_search_file(self, query: str, page: int = 1) -> MultiSearch:
        """Return MultiSearch file."""
        return self._file(MultiSearch, query, page)

    # TODO: Validate
    def title_page_file(self, media_type: str, tmdb_id: int) -> TitlePage:
        """Return TitlePage file."""
        return self._file(TitlePage, media_type, tmdb_id)

    # TODO: Validate
    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Return MovieSearch file."""
        return self._file(MovieSearch, query, year)

    # TODO: Validate
    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Return TvSearch file."""
        return self._file(TvSearch, query, year)

    # TODO: Validate
    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Return MovieDetails file."""
        return self._file(MovieDetails, str(tmdb_id))

    # TODO: Validate
    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Return ShowDetail file."""
        return self._file(ShowDetail, tmdb_id)

    # TODO: Validate
    def changes_since(self, show_key: str) -> date:
        show = Show.get(self.session, self.source, show_key)
        reference = show.update_at if show and show.update_at else tz_datetime.now()
        return (reference - CHANGES_OVERLAP).date()

    # TODO: Validate
    def _latest_show_changes_dates(self) -> dict[int, date | None]:
        cached: dict[int, date | None] = self.session.info.setdefault(
            _LATEST_SHOW_CHANGES_DATES,
            {},
        )
        return cached

    # TODO: Validate
    def _latest_show_changes_date(self, tmdb_show_id: int) -> date | None:
        cached = self._latest_show_changes_dates()
        if tmdb_show_id in cached:
            return cached[tmdb_show_id]

        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{ShowChanges.__name__}/{tmdb_show_id}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        stored = self.session.exec(statement).first()
        if stored is None:
            cached[tmdb_show_id] = None
            return None
        identifier = ShowChanges.file_key_to_unique_identifier(stored.key)
        latest = date.fromisoformat(identifier.split("/")[-1])
        cached[tmdb_show_id] = latest
        return latest

    # TODO: Validate
    def show_changes_file(
        self,
        show_key: str,
        downloaded_to: date | None = None,
    ) -> ShowChanges:
        """Return ShowChanges file."""
        _, tmdb_id = parse_show_key(show_key)
        if downloaded_to is None:
            downloaded_to = (
                self._latest_show_changes_date(tmdb_id) or tz_datetime.now().date()
            )
        else:
            self._latest_show_changes_dates().pop(tmdb_id, None)
        return self._file(
            ShowChanges,
            tmdb_id,
            self.changes_since(show_key),
            downloaded_to,
        )

    # TODO: Validate
    def incomplete_show_changes_files(self, show_key: str) -> list[ShowChanges]:
        """Return every ShowChanges file for a title not yet read to the end."""
        _, tmdb_id = parse_show_key(show_key)
        since = self.changes_since(show_key)
        return self.get_incomplete_files(
            ShowChanges,
            lambda stored: self._file(
                ShowChanges,
                tmdb_id,
                since,
                date.fromisoformat(
                    ShowChanges.file_key_to_unique_identifier(stored.key).split("/")[
                        -1
                    ],
                ),
            ),
            key_prefix=f"{tmdb_id}/",
        )

    # TODO: Validate
    def stored_episode_translations_files(
        self,
        tmdb_show_id: int,
    ) -> list[EpisodeTranslations]:
        """Return every EpisodeTranslations file already held for a title."""
        statement = select(File).where(
            File.plugin == self.plugin,
            col(File.key).startswith(
                f"{EpisodeTranslations.__name__}/{tmdb_show_id}/",
            ),
        )
        files: list[EpisodeTranslations] = []
        for stored in self.session.exec(statement).all():
            identifier = EpisodeTranslations.file_key_to_unique_identifier(stored.key)
            _, season_number, episode_number = identifier.split("/")
            files.append(
                self.episode_translations_file(
                    tmdb_show_id,
                    int(season_number),
                    int(episode_number),
                ),
            )
        return files

    # TODO: Validate
    def episode_groups_file(self, tmdb_id: int) -> EpisodeGroups:
        """Return the EpisodeGroups file for a title."""
        return self._file(EpisodeGroups, tmdb_id)

    # TODO: Validate
    def episode_group_detail_file(self, group_id: str) -> EpisodeGroupDetail:
        """Return the EpisodeGroupDetail file for one episode order."""
        return self._file(EpisodeGroupDetail, group_id)

    # TODO: Validate
    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Return SeasonDetail file."""
        return self._file(SeasonDetail, tmdb_show_id, season_number)

    # TODO: Validate
    def episode_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeDetail:
        """Return EpisodeDetail file."""
        return self._file(
            EpisodeDetail,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def episode_translations_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeTranslations:
        """Return EpisodeTranslations file."""
        return self._file(
            EpisodeTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Return TvSeriesDetails file."""
        return self._file(TvSeriesDetails, str(tmdb_id))

    # TODO: Validate
    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Return MovieWatchProviders file."""
        return self._file(MovieWatchProviders, str(tmdb_id))

    # TODO: Validate
    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Return TvWatchProviders file."""
        return self._file(TvWatchProviders, str(tmdb_id))

    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvSeriesDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails: ...
    # TODO: Validate
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails:
        """Return MovieDetails or TvSeriesDetails file."""
        if media_type == MediaType.movie:
            return self.movie_detail_file(tmdb_id)
        return self.tv_detail_file(tmdb_id)

    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders: ...
    # TODO: Validate
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        """Return MovieWatchProviders or TvWatchProviders file."""
        if media_type == MediaType.movie:
            return self.movie_watch_providers_file(tmdb_id)
        return self.tv_watch_providers_file(tmdb_id)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        groups_file = self.episode_groups_file(tmdb_id)
        groups_file.download_if_outdated()
        return [
            self.show_changes_file(show_key),
            self.show_detail_file(tmdb_id),
            groups_file,
            *(
                self.episode_group_detail_file(option.id)
                for option in self._episode_group_options(tmdb_id)
            ),
        ]

    # TODO: Validate
    def _episode_group_options(
        self,
        tmdb_id: int,
    ) -> Sequence[EpisodeGroupSummary]:
        """Return every episode order TMDB lists for a title.

        A title TMDB holds no orders for, and one the endpoint has nothing to
        say about at all, both read as none rather than raising: an order is
        something a title may simply not have.
        """
        groups_file = self.episode_groups_file(tmdb_id)
        if not groups_file.database_record.content:
            return []
        return groups_file.parsed().results

    # TODO: Validate
    def _chosen_group_id(self, show_key: str) -> str | None:
        """Return the episode order this title is read in, where one was chosen.

        Read off the stored `Show` rather than off a file, since the choice is a
        `User`'s and nothing TMDB says. A title being imported for the first time
        has no row to have chosen anything yet, which reads as TMDB's own order.
        """
        show = Show.get(self.session, self.source, show_key)
        return chosen_group_id(show.extra) if show else None

    # TODO: Validate
    def _chosen_group(self, show_key: str) -> TvEpisodeGroupModel | None:
        """Return the chosen episode order itself, where there is one."""
        group_id = self._chosen_group_id(show_key)
        if group_id is None:
            return None
        return self.episode_group_detail_file(group_id).parsed()

    # TODO: Validate
    def series_seasons(self, show_key: str) -> list[SeasonSource]:
        """Return the seasons of a series, in whichever order it is read in.

        A chosen order replaces the title's own outright: its groups are the
        seasons and its episodes are numbered by where the order puts them, not
        by where TMDB's own seasons did. The episodes keep their own ids either
        way, so the same episode is the same row whichever order it is read in
        and a title changing order moves its episodes rather than replacing them.
        """
        _, tmdb_id = parse_show_key(show_key)
        group = self._chosen_group(show_key)
        if group is not None:
            return [
                SeasonSource(
                    key=season_key(MediaType.tv, order),
                    name=entry.name,
                    season_number=order + 1,
                    poster_path=None,
                    episodes=[
                        EpisodeSource(number=number, entry=episode)
                        for number, episode in enumerate(entry.episodes, start=1)
                    ],
                )
                for order, entry in enumerate(group.groups)
            ]

        seasons: list[SeasonSource] = []
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            season_file = self.season_detail_file(tmdb_id, season.season_number)
            # Downloaded here rather than left to the caller for the same reason
            # the orders are: what says which seasons a title has is the title's
            # own file, so nothing can name a season file before that has been
            # read, and a title being imported for the first time has none of
            # them stored to be read out of.
            season_file.download_if_outdated()
            # A season the title lists but TMDB has no detail for is stored
            # empty, and an empty file has nothing to read a season out of.
            if not season_file.database_record.content:
                continue
            detail = season_file.parsed()
            seasons.append(
                SeasonSource(
                    key=season_key(MediaType.tv, season.id),
                    name=detail.name,
                    season_number=season.season_number,
                    poster_path=detail.poster_path,
                    episodes=[
                        EpisodeSource(number=episode.episode_number, entry=episode)
                        for episode in detail.episodes
                    ],
                ),
            )
        return seasons

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        changes_file = self.show_changes_file(show_key)
        group_id = self._chosen_group_id(show_key)
        if group_id is not None:
            return [changes_file, self.episode_group_detail_file(group_id)]
        return [
            changes_file,
            self.season_detail_file(
                tmdb_id,
                self._native_season_number(season_key, show_key),
            ),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the file an episode was read out of, which is its season's.

        A season carries every episode of it, so that one file is where an
        episode's own record comes from and what says how current it is. TMDB
        does hold a file per episode, but nothing here is read from it: what
        wants one - matching a website's episode to TMDB's by name - downloads
        it as it gets there, and naming it here would have every import fetch
        two files an episode for nothing.
        """
        return self._season_files(season_key, show_key)

    # TODO: Validate
    def _native_season_number(self, season_key: str, show_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, season_tmdb_id = parse_season_key(season_key)
        _, tmdb_id = parse_show_key(show_key)
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            if season.id == season_tmdb_id:
                return season.season_number
        message = f"{show_key} has no season {season_key}"
        raise ValueError(message)
