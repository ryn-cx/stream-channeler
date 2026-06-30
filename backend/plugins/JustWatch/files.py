# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from functools import cache
from typing import Any, override

import httpx
from just_scrape import JustScrape
from just_scrape.custom_buy_box_offers import (
    response_models as custom_buy_box_offers_models,
)
from just_scrape.custom_season_episodes import (
    response_models as custom_season_episodes_models,
)
from just_scrape.exceptions import GraphQLError
from just_scrape.new_title_buckets import response_models as new_title_buckets_models
from just_scrape.new_titles import response_models as new_titles_models
from just_scrape.search import response_models as search_models
from just_scrape.url_title_details import response_models as url_title_details_models
from sqlalchemy import ScalarResult
from sqlmodel import Session, col, select

from app.config import settings
from app.plugins.models import File, Plugin
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin, JSONFile
from plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON

_MEDIA_TYPE_MAP = {"SHOW": "TV Show", "MOVIE": "Movie"}


@cache
def just_scrape() -> JustScrape:
    server: str | None = settings.GET_AROUND_SERVER
    if server == "changethis":
        server = None
    password: str | None = settings.GET_AROUND_PASSWORD
    if password == "changethis":  # noqa: S105
        password = None
    return JustScrape(
        get_around_server=server,
        get_around_password=password,
        sleep_time=10,
    )


class NewTitles(GAPIListJSON[new_titles_models.NewTitlesResponse]):
    api_endpoint = just_scrape().new_titles

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        source_key: str,
        date: date,
    ) -> None:
        self.source_key = source_key
        self.date = date
        super().__init__(session, plugin, f"{source_key}/{date}")

    @override
    def _get(self) -> list[new_titles_models.NewTitlesResponse]:
        return just_scrape().new_titles.get_all_for_date(
            available_to_packages=[self.source_key],
            filter_packages=[self.source_key],
            date=self.date,
        )

    def parsed_edges(self) -> list[new_titles_models.Edge]:
        return just_scrape().new_titles.extract_edges(self.parsed())


class NewTitleBucket(GAPIListJSON[new_title_buckets_models.NewTitleBucketsResponse]):
    api_endpoint = just_scrape().new_title_buckets

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
        return just_scrape().new_title_buckets.get_all_since_date(end_date)

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
            self._write(response.json())

    # TODO: Add this to Just Scrape so it has full type support.
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return raw


class UrlTitleDetails(GAPIJSON[url_title_details_models.UrlTitleDetailsResponse]):
    api_endpoint = just_scrape().url_title_details

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._get()
                content = self.api_endpoint.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid URL.
            except GraphQLError:
                self._write(None)


class CustomSeasonEpisodes(
    GAPIListJSON[custom_season_episodes_models.CustomSeasonEpisodesResponse],
):
    api_endpoint = just_scrape().custom_season_episodes

    @override
    def _get(self) -> list[custom_season_episodes_models.CustomSeasonEpisodesResponse]:
        return just_scrape().custom_season_episodes.get_all(self.unique_identifier)

    def parsed_episodes(self) -> list[custom_season_episodes_models.Episode]:
        return just_scrape().custom_season_episodes.extract_episodes(self.parsed())


class CustomBuyBoxOffers(
    GAPIJSON[custom_buy_box_offers_models.CustomBuyBoxOffersResponse],
):
    api_endpoint = just_scrape().custom_buy_box_offers


class SearchTitles(GAPIJSON[search_models.SearchResponse]):
    api_endpoint = just_scrape().search


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._cached_media_type = None

    def custom_buy_box_offers_file(self, episode_key: str) -> CustomBuyBoxOffers:
        """Return a cached custom buy box offers file for the given episode key."""
        return self._get_cached_file(
            CustomBuyBoxOffers,
            episode_key,
            lambda: CustomBuyBoxOffers(self.session, self.plugin, episode_key),
        )

    def url_title_details_file(self, show_key: str) -> UrlTitleDetails:
        """Return a cached url title details file for the given show key."""
        return self._get_cached_file(
            UrlTitleDetails,
            show_key,
            lambda: UrlTitleDetails(self.session, self.plugin, show_key),
        )

    def new_titles_file(self, source_key: str, date: datetime | date) -> NewTitles:
        """Return a cached new titles file for the given source key and date."""
        if isinstance(date, datetime):
            date = date.date()

        cache_key = f"{source_key}_{date}"
        return self._get_cached_file(
            NewTitles,
            cache_key,
            lambda: NewTitles(self.session, self.plugin, source_key, date),
        )

    def custom_season_episodes_file(self, season_key: str) -> CustomSeasonEpisodes:
        """Return a cached custom season episodes file for the given season key."""
        return self._get_cached_file(
            CustomSeasonEpisodes,
            season_key,
            lambda: CustomSeasonEpisodes(self.session, self.plugin, season_key),
        )

    def new_titles_bucket_file(self, end_datetime: datetime | File) -> NewTitleBucket:
        """Return a cached new titles bucket file for the given datetime or File."""
        if isinstance(end_datetime, File):
            key = NewTitleBucket.file_key_to_unique_identifier(end_datetime.key)
            end_datetime = datetime.fromisoformat(key)
        return self._get_cached_file(
            NewTitleBucket,
            end_datetime,
            lambda: NewTitleBucket(self.session, self.plugin, end_datetime),
        )

    def providers_locale_file(self, locale: str = "en_US") -> ProvidersLocale:
        """Return a cached providers locale file for the given locale."""
        return self._get_cached_file(
            ProvidersLocale,
            locale,
            lambda: ProvidersLocale(self.session, self.plugin, locale),
        )

    def search_titles_file(self, query: str) -> SearchTitles:
        """Return a cached search titles file for the given query."""
        return self._get_cached_file(
            SearchTitles,
            query,
            lambda: SearchTitles(self.session, self.plugin, query),
        )

    @override
    def _plugin_files(self) -> Sequence[ProvidersLocale | NewTitleBucket]:
        # Doesn't actually return all of the files, only the latest versions,
        return [
            self.providers_locale_file(),
            self.new_titles_bucket_file(self._get_latest_new_titles_bucket().one()),
        ]

    @override
    def _show_files(self, show_key: str) -> Sequence[UrlTitleDetails]:
        # Movies - Required to detect changes to the show (there are no new seasons).
        # TV Show - Required to detect changes to the show and new seasons.
        return [self.url_title_details_file(show_key)]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the season.
            return [self.url_title_details_file(show_key)]
        return [
            # Required to detect new episodes.
            self.custom_season_episodes_file(season_key),
            # Required to detect changes to the season.
            self.url_title_details_file(show_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes | CustomBuyBoxOffers]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the episode.
            return [self.url_title_details_file(show_key)]

        return [
            # Required to detect changes to the episode.
            self.custom_buy_box_offers_file(episode_key),
            self.custom_season_episodes_file(season_key),
        ]

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
            for episode in self.custom_season_episodes_file(
                season_key,
            ).parsed_episodes()
        ]

    def _media_type(self, show_key: str) -> str:
        if not self._cached_media_type:
            url_title_details = self.url_title_details_file(show_key).parsed()
            raw_media_type = url_title_details.data.url_v2.node.object_type
            self._cached_media_type = _MEDIA_TYPE_MAP[raw_media_type]  # type: ignore[assignment]
        return self._cached_media_type  # type: ignore[return-value]

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

    def _get_latest_new_titles_bucket(self) -> ScalarResult[File]:
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
            .limit(1)
        )
        return self.session.exec(statement)

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
