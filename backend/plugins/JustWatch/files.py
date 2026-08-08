# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from functools import cache
from typing import Any, cast, override

import httpx
from get_around import GetAround
from good_ass_pydantic_integrator import ParseLevel
from just_scrape import JustScrape
from just_scrape.buy_box_offers import models as buy_box_offers_models
from just_scrape.exceptions import GraphQLError
from just_scrape.new_title_buckets import models as new_title_buckets_models
from just_scrape.new_titles import models as new_titles_models
from just_scrape.search import models as search_models
from just_scrape.season_episodes import models as season_episodes_models
from just_scrape.url_title_details import models as url_title_details_models
from sqlalchemy import ScalarResult
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.config import settings
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    BaseFile,
    GAPIListJSON,
    JSONFile,
)
from plugins.utils.get_around_client import get_around_client

_MEDIA_TYPE_MAP = {"SHOW": "TV Show", "MOVIE": "Movie"}


# The worker is shared by every plugin and JustWatch is what leans on it hardest,
# so its requests go through a proxy of our own whenever one is configured and
# fall back to the worker when it is not.
@cache
def _just_watch_client() -> GetAround:
    if settings.PROXY:
        return GetAround(proxy=settings.PROXY)
    return get_around_client()


@cache
def just_scrape() -> JustScrape:
    # Nothing but this shares the proxy, so there is nothing to pace it against.
    sleep_time = 0 if settings.PROXY else 5
    return JustScrape(
        get_around_client=_just_watch_client(),
        sleep_time=sleep_time,
    )


# The throttle above paces the bulk downloads that run in the background, where
# waiting costs nothing. A search happens while a user is watching the screen,
# so it gets a client that returns as soon as the response arrives.
@cache
def unthrottled_just_scrape() -> JustScrape:
    return JustScrape(get_around_client=_just_watch_client())


class NewTitles(GAPIListJSON[new_titles_models.NewTitlesResponse]):
    API_ENDPOINT = just_scrape().new_titles

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        source_key: str,
        new_titles_date: date,
    ) -> None:
        self.source_key = source_key
        self.date = new_titles_date
        super().__init__(session, plugin, f"{source_key}/{new_titles_date}")

    @override
    def _get(self) -> list[new_titles_models.NewTitlesResponse]:
        return just_scrape().new_titles.download_and_parse_for_date(
            available_to_packages=[self.source_key],
            filter_packages=[self.source_key],
            date=self.date,
        )

    def parsed_edges(self) -> list[new_titles_models.Edge]:
        return just_scrape().new_titles.extract_edges(self.parsed())


class NewTitleBucket(GAPIListJSON[new_title_buckets_models.NewTitleBucketsResponse]):
    API_ENDPOINT = just_scrape().new_title_buckets

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        end_datetime: datetime,
    ) -> None:
        self.end_datetime = end_datetime
        super().__init__(session, plugin, str(end_datetime))

    @override
    def _get(self) -> list[new_title_buckets_models.NewTitleBucketsResponse]:
        end_date = self.end_datetime.date()
        return just_scrape().new_title_buckets.download_and_parse_since_date(end_date)

    def parsed_edges(self) -> list[new_title_buckets_models.Edge]:
        return just_scrape().new_title_buckets.extract_edges(self.parsed())


class ProvidersLocale(JSONFile[list[dict[str, Any]]]):
    def __init__(self, session: Session, plugin: Plugin, locale: str) -> None:
        self.unique_identifier = locale
        super().__init__(session, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            url = f"https://apis.justwatch.com/content/providers/locale/{self.unique_identifier}"
            response = httpx.get(url)
            response.raise_for_status()
            self.write(response.json())

    # TODO: Add this to Just Scrape so it has full type support.
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return cast("list[dict[str, Any]]", raw)


class UrlTitleDetails(GAPIJSON[url_title_details_models.UrlTitleDetailsResponse]):
    API_ENDPOINT = just_scrape().url_title_details

    # Occurs when a user puts in an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, GraphQLError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid full_path {self.unique_identifier}"


class SeasonEpisodes(
    GAPIListJSON[season_episodes_models.SeasonEpisodesResponse],
):
    API_ENDPOINT = just_scrape().season_episodes

    @override
    def _get(self) -> list[season_episodes_models.SeasonEpisodesResponse]:
        return just_scrape().season_episodes.download_and_parse_all(
            self.unique_identifier,
        )

    def parsed_episodes(self) -> list[season_episodes_models.Episode]:
        """Return every episode across the file's pages.

        Flattened here rather than through `extract_episodes`, which decides what
        it was handed with `isinstance`. A download that does not fit the model
        makes GAPI regenerate and reload it, and the reloaded class is a
        different object than the one that helper closed over, so the check
        silently fails and it recurses into the value until the stack runs out.
        """
        return [
            episode for page in self.parsed() for episode in page.data.node.episodes
        ]


class BuyBoxOffers(
    GAPIJSON[buy_box_offers_models.BuyBoxOffersResponse],
):
    API_ENDPOINT = just_scrape().buy_box_offers


class SearchTitles(GAPIJSON[search_models.SearchResponse]):
    API_ENDPOINT = unthrottled_just_scrape().search

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        cursor: str,
    ) -> None:
        self.query = query
        self.cursor = cursor
        super().__init__(session, plugin, f"{query}/{cursor}")

    # Every argument but the cursor keeps its default so a page request looks
    # exactly like the one the website makes.
    @override
    def _get(self) -> search_models.SearchResponse:
        return unthrottled_just_scrape().search.download_and_parse(
            self.query,
            search_after_cursor=self.cursor,
        )


class FileMixin(TMDBMixin, register=False):
    _cached_media_type: str | None = None

    # The provider list and the new titles feeds belong to the plugin and its
    # sources, so every show reads the same ones.
    _PLUGIN_WIDE_FILES = (ProvidersLocale, NewTitleBucket, NewTitles)

    def buy_box_offers_file(self, episode_key: str) -> BuyBoxOffers:
        """Contains every offer JustWatch has for a single episode."""
        return self._file(BuyBoxOffers, episode_key)

    def url_title_details_file(self, show_key: str) -> UrlTitleDetails:
        """Contains a title's metadata, its seasons, and its offers."""
        return self._file(UrlTitleDetails, show_key)

    def new_titles_file(self, source_key: str, new_date: datetime | date) -> NewTitles:
        """Contains the titles a single source added on a single date."""
        if isinstance(new_date, datetime):
            new_date = new_date.date()
        return self._file(NewTitles, source_key, new_date)

    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        """Contains every episode of a single season."""
        return self._file(SeasonEpisodes, season_key)

    def episode_has_offers(self, episode_key: str, season_key: str) -> bool:
        """Report whether JustWatch has anywhere to watch an episode.

        A season's episode list already carries how many offers each of its
        episodes has, so an episode with none is known to have nothing to watch
        before its buy box offers are asked for. Asking would answer the same
        nothing, and a title no service carries would ask once per episode for
        it.
        """
        return any(
            episode.unique_offer_count
            for episode in self.season_episodes_file(season_key).parsed_episodes()
            if episode.id == episode_key
        )

    def new_titles_bucket_file(self, end_datetime: datetime | File) -> NewTitleBucket:
        """Contains which sources added new titles on which dates."""
        if isinstance(end_datetime, File):
            key = NewTitleBucket.file_key_to_unique_identifier(end_datetime.key)
            end_datetime = datetime.fromisoformat(key)
        return self._file(NewTitleBucket, end_datetime)

    def providers_locale_file(self, locale: str = "en_US") -> ProvidersLocale:
        """Contains every provider JustWatch tracks for a locale."""
        return self._file(ProvidersLocale, locale)

    def search_titles_file(self, query: str, cursor: str | None) -> SearchTitles:
        """Contains one page of search results for a single query."""
        return self._file(SearchTitles, query, cursor or "")

    @override
    def _plugin_files(self) -> Sequence[ProvidersLocale | NewTitleBucket]:
        # Doesn't actually return all of the files, only the latest versions,
        return [
            self.providers_locale_file(),
            self.new_titles_bucket_file(self._get_latest_new_titles_bucket().one()),
        ]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Movies - Required to detect changes to the show (there are no new seasons).
        # TV Show - Required to detect changes to the show and new seasons.
        base_files = [self.url_title_details_file(show_key)]
        return self._append_tmdb_show_file(base_files, show_key)

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the season.
            base_files = [self.url_title_details_file(show_key)]
        else:
            base_files = [
                # Required to detect new episodes.
                self.season_episodes_file(season_key),
                # Required to detect changes to the season.
                self.url_title_details_file(show_key),
            ]
        return self._append_tmdb_season_file(base_files, season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the episode.
            base_files = [self.url_title_details_file(show_key)]
        elif self.episode_has_offers(episode_key, season_key):
            base_files = [
                # Required to detect changes to the episode.
                self.buy_box_offers_file(episode_key),
                self.season_episodes_file(season_key),
            ]
        else:
            # An episode with nowhere to watch it is not stored, so its offers
            # are never read and are left undownloaded.
            base_files = [self.season_episodes_file(season_key)]
        return self._append_tmdb_episode_file(
            base_files,
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _download_season_files_and_children(
        self,
        season: str | Season,
        show: str | Show | None = None,
        update_at: datetime | None = None,
    ) -> list[File]:
        season_key = self._get_key(season)
        show_key = self._get_show_key(season, show)
        files = super()._download_season_files_and_children(
            season_key,
            show_key,
            update_at,
        )
        # Episode files are only downloaded when missing, so the buy box offers
        # are refreshed here to pick up offer changes for existing episodes.
        if self._media_type(show_key) != "Movie":
            for episode in self.season_episodes_file(season_key).parsed_episodes():
                if not episode.unique_offer_count:
                    continue
                self.buy_box_offers_file(episode.id).download_if_outdated(update_at)
        return files

    def _download_new_titles_files(
        self,
        new_titles_files: list[NewTitles],
    ) -> None:
        for new_titles_file in new_titles_files:
            new_titles_file.download_if_outdated()
            minimum_timestamp = self.minimum_new_titles_timestamp(new_titles_file)
            if minimum_timestamp <= tz_datetime.now():
                new_titles_file.download_if_outdated(minimum_timestamp)

    def _pending_new_titles_files(self, source: Source) -> list[NewTitles]:
        # Files not yet marked "Completed" in File.extra are still pending.
        def factory(file: File) -> NewTitles:
            unique_identifier = NewTitles.file_key_to_unique_identifier(file.key)
            new_titles_date = date.fromisoformat(unique_identifier.rsplit("/", 1)[-1])
            return self.new_titles_file(source.key, new_titles_date)

        return self.get_incomplete_files(
            NewTitles,
            factory,
            key_prefix=f"{source.key}/",
        )

    def _download_new_titles_bucket_if_missing(self) -> None:
        if not self._get_latest_new_titles_bucket().first():
            bucket = self.new_titles_bucket_file(tz_datetime.now() - timedelta(days=1))
            bucket.download_if_outdated()

    def _download_new_titles(self) -> None:
        """Download every new titles file the stored buckets list.

        The buckets say which dates a provider added titles on and the new titles
        files are what `update_source` reads. Every provider is covered because a
        service only announces a title it picked up in its own feed, so the feeds
        that report a title becoming available somewhere new are the ones for the
        services it is not on yet. A file that is never downloaded has no record
        for `_pending_new_titles_files` to find, leaving it invisible for good.
        """
        new_titles_files = [
            self.new_titles_file(edge.key.package.short_name, edge.key.date)
            for bucket_record in self._get_new_titles_buckets()
            for edge in self.new_titles_bucket_file(bucket_record).parsed_edges()
        ]
        # Read every stored record in one query and hold it for the loop below.
        # The session only keeps records weakly, so without this each file finds
        # nothing in memory and queries the database for its own record.
        _cache = self._get_files_by_keys(
            [new_titles.file_key() for new_titles in new_titles_files],
        )
        for new_titles in new_titles_files:
            new_titles.download_if_outdated()

    def provider(self, source_key: str) -> dict[str, Any]:
        """Return the providers file's entry for `source_key`."""
        providers = self._providers_by_key()
        if source_key not in providers:
            # A provider JustWatch added after the providers file was downloaded.
            self.providers_locale_file().download_if_outdated(tz_datetime.now())
            providers = self._providers_by_key()
        return providers[source_key]

    def _providers_by_key(self) -> dict[str, dict[str, Any]]:
        return {
            provider["short_name"]: provider
            for provider in self.providers_locale_file().parsed()
        }

    def _download_latest_new_titles_bucket(self) -> None:
        latest_bucket = self._get_latest_new_titles_bucket().one()
        # If the bucket was last updated within a day nothing needs to be done.
        if latest_bucket.data_timestamp > tz_datetime.now() - timedelta(days=1):
            return

        # All other situations a new bucket should be downloaded.
        end_datetime = latest_bucket.data_timestamp - timedelta(days=1)
        bucket = self.new_titles_bucket_file(end_datetime)
        bucket.download_if_outdated()

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        url_title_details = self.url_title_details_file(show_key).parsed()
        node = url_title_details.data.url_v2.node
        if seasons := node.seasons:
            return [season.id for season in seasons]
        # Movies have no real seasons, but `_upsert_movie_season` creates a
        # virtual season whose key is the movie's node id.
        return [node.id]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if self._cached_media_type == "Movie":
            return []
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.id
            for season_key in season_keys
            for episode in self.season_episodes_file(season_key).parsed_episodes()
        ]

    def _media_type(self, show_key: str) -> str:
        if not self._cached_media_type:
            url_title_details = self.url_title_details_file(show_key).parsed()
            raw_media_type = url_title_details.data.url_v2.node.object_type
            self._cached_media_type = _MEDIA_TYPE_MAP[raw_media_type]
        return self._cached_media_type

    def _sources_with_offers(
        self,
        show_key: str,
    ) -> list[tuple[str, url_title_details_models.Offer]]:
        """Get all unique sources with their first corresponding offer."""
        seen: dict[str, url_title_details_models.Offer] = {}
        url_title_details = self.url_title_details_file(show_key).parsed()
        for offer in url_title_details.data.url_v2.node.offers:
            # If a website offers multiple different plans the data will be duplicated
            # for each plan so only use the first offer for each source.
            seen.setdefault(offer.package.short_name, offer)
        return list(seen.items())

    def _new_titles_buckets_statement(self) -> SelectOfScalar[File]:
        return (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )

    def _get_new_titles_buckets(self) -> ScalarResult[File]:
        return self.session.exec(self._new_titles_buckets_statement())

    def _get_latest_new_titles_bucket(self) -> ScalarResult[File]:
        return self.session.exec(self._new_titles_buckets_statement().limit(1))

    def minimum_new_titles_timestamp(self, file: NewTitles) -> datetime:
        # The data for a specific source changes throughout the day as new entries are
        # appended to existing ones as can be seen here.
        # https://web.archive.org/web/20250327001549/https://www.justwatch.com/us/new
        # https://web.archive.org/web/20250327144339/https://www.justwatch.com/us/new
        # https://web.archive.org/web/20250327170119/https://www.justwatch.com/us/new
        # Therefore, extra buffer is needed to make sure all of the data for a specific
        # date is captured. A buffer of 2 days used to allow 1 day for possible timezone
        # differences and another day to for all of the entries for a single day to
        # exist.
        return tz_datetime.combine(file.date, datetime.min.time()) + timedelta(days=2)
