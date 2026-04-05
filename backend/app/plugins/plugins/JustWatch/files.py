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
from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_plugin import BasePlugin, JSONFile
from app.plugins.plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime

_MEDIA_TYPE_MAP = {"SHOW": "TV Show", "MOVIE": "Movie"}


@cache
def just_scrape_client() -> JustScrape:
    return JustScrape(
        get_around_server=settings.GET_AROUND_SERVER,
        get_around_password=settings.GET_AROUND_PASSWORD,
    )


class NewTitles(GAPIListJSON[new_titles_models.NewTitlesResponse]):
    api_endpoint = just_scrape_client().new_titles

    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        source_key: str,
        date: date,
    ) -> None:
        self.source_key = source_key
        self.date = date
        super().__init__(db, plugin, f"{source_key}/{date}")

    @override
    def _get(self) -> list[new_titles_models.NewTitlesResponse]:
        return just_scrape_client().new_titles.get_all_for_date(
            available_to_packages=[self.source_key],
            filter_packages=[self.source_key],
            date=self.date,
        )

    def parsed_edges(self) -> list[new_titles_models.Edge]:
        return just_scrape_client().new_titles.extract_edges(self.parsed())


class NewTitleBucket(GAPIListJSON[new_title_buckets_models.NewTitleBucketsResponse]):
    api_endpoint = just_scrape_client().new_title_buckets

    def __init__(self, db: Session, plugin: Plugin, end_datetime: datetime) -> None:
        self.end_datetime = end_datetime
        super().__init__(db, plugin, str(end_datetime))

    @override
    def _get(self) -> list[new_title_buckets_models.NewTitleBucketsResponse]:
        return just_scrape_client().new_title_buckets.get_all_since_date(
            end_date=self.end_datetime.date(),
        )

    def parsed_edges(self) -> list[new_title_buckets_models.Edge]:
        return just_scrape_client().new_title_buckets.extract_edges(self.parsed())


class ProvidersLocale(JSONFile[list[dict[str, Any]]]):
    def __init__(self, db: Session, plugin: Plugin, locale: str) -> None:
        self.unique_identifier = locale
        super().__init__(db, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = httpx.get(
                f"https://apis.justwatch.com/content/providers/locale/{self.unique_identifier}",
            )
            response.raise_for_status()
            self._write(response.json())

    # TODO: Add scraping this to Just Scrape so the code here can be simplified.
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return raw


class UrlTitleDetails(GAPIJSON[url_title_details_models.UrlTitleDetailsResponse]):
    api_endpoint = just_scrape_client().url_title_details

    # TODO: Can this error be handled better?
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
    api_endpoint = just_scrape_client().custom_season_episodes

    @override
    def _get(self) -> list[custom_season_episodes_models.CustomSeasonEpisodesResponse]:
        return just_scrape_client().custom_season_episodes.get_all(
            node_id=self.unique_identifier,
        )

    def parsed_episodes(self) -> list[custom_season_episodes_models.Episode]:
        return just_scrape_client().custom_season_episodes.extract_episodes(
            self.parsed(),
        )


class CustomBuyBoxOffers(
    GAPIJSON[custom_buy_box_offers_models.CustomBuyBoxOffersResponse],
):
    api_endpoint = just_scrape_client().custom_buy_box_offers


class SearchTitles(GAPIJSON[search_models.SearchResponse]):
    api_endpoint = just_scrape_client().search


class FileMixin(BasePlugin, register=False):
    # region File Cache

    @override
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )
        self._cached_media_type = None

    def _custom_buy_box_offers_file(self, episode_key: str) -> CustomBuyBoxOffers:
        return self._get_weakref_cached_file(
            CustomBuyBoxOffers,
            episode_key,
            lambda: CustomBuyBoxOffers(self.db, self.plugin, episode_key),
        )

    def _url_title_details_file(self, show_key: str) -> UrlTitleDetails:
        return self._get_weakref_cached_file(
            UrlTitleDetails,
            show_key,
            lambda: UrlTitleDetails(self.db, self.plugin, show_key),
        )

    def _new_titles_file(self, source_key: str, date: datetime | date) -> NewTitles:
        if isinstance(date, datetime):
            date = date.date()

        cache_key = f"{source_key}_{date}"
        return self._get_weakref_cached_file(
            NewTitles,
            cache_key,
            lambda: NewTitles(self.db, self.plugin, source_key, date),
        )

    def _custom_season_episodes_file(self, season_key: str) -> CustomSeasonEpisodes:
        return self._get_weakref_cached_file(
            CustomSeasonEpisodes,
            season_key,
            lambda: CustomSeasonEpisodes(self.db, self.plugin, season_key),
        )

    def _new_titles_bucket_file(
        self,
        end_datetime: datetime | File,
    ) -> NewTitleBucket:
        if isinstance(end_datetime, File):
            key = NewTitleBucket.file_key_to_unique_identifier(end_datetime.key)
            end_datetime = datetime.fromisoformat(key)
        return self._get_weakref_cached_file(
            NewTitleBucket,
            end_datetime,
            lambda: NewTitleBucket(self.db, self.plugin, end_datetime),
        )

    def _providers_locale_file(self, locale: str = "en_US") -> ProvidersLocale:
        return self._get_weakref_cached_file(
            ProvidersLocale,
            locale,
            lambda: ProvidersLocale(self.db, self.plugin, locale),
        )

    def _search_titles_file(self, query: str) -> SearchTitles:
        return self._get_weakref_cached_file(
            SearchTitles,
            query,
            lambda: SearchTitles(self.db, self.plugin, query),
        )

    # endregion File Cache

    def _source_keys_from_buckets(self, db: Session, plugin: Plugin) -> set[str]:
        """Get all source keys with new titles from unimported bucket files."""
        statement = select(File).where(
            File.plugin_id == plugin.id,
            col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
            col(File.data_timestamp) > plugin.data_timestamp,
        )
        source_keys: set[str] = set()
        for file in db.exec(statement).all():
            bucket = self._new_titles_bucket_file(file)
            for edge in bucket.parsed_edges():
                source_keys.add(edge.key.package.short_name)
        return source_keys

    # region File Groups

    @override
    def _show_files(self, show_key: str, **kwargs: Any) -> Sequence[UrlTitleDetails]:  # type: ignore[override]
        # Movies - Required to detect changes to the show (there are no new seasons).
        # TV Show - Required to detect changes to the show and new seasons.
        return [self._url_title_details_file(show_key)]

    @override
    def _season_files(  # type: ignore[override]
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the season.
            return [self._url_title_details_file(show_key)]
        return [
            # Required to detect new episodes.
            self._custom_season_episodes_file(season_key),
            # Required to detect changes to the season.
            self._url_title_details_file(show_key),
        ]

    @override
    def _episode_files(  # type: ignore[override]
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes | CustomBuyBoxOffers]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the episode.
            return [self._url_title_details_file(show_key)]

        return [
            # Required to detect changes to the episode.
            self._custom_buy_box_offers_file(episode_key),
            self._custom_season_episodes_file(season_key),
        ]

    # endregion File Groups

    # region Download

    def _download_new_titles_files(
        self,
        source: Source,
        dates: list[date],
    ) -> None:
        for new_titles_date in dates:
            new_titles_file = self._new_titles_file(source.key, new_titles_date)
            new_titles_file.download_if_outdated()
            minimum_timestamp = self.minimum_new_titles_data_timestamp(new_titles_file)
            if minimum_timestamp <= tz_datetime.now():
                new_titles_file.download_if_outdated(minimum_timestamp)

    def _download_latest_new_titles_bucket(self) -> None:
        latest_bucket = self._get_latest_new_titles_bucket().first()
        # If no buckets exist download the initial one with a 1 day buffer worth of
        # data.
        if not latest_bucket:
            bucket = self._new_titles_bucket_file(tz_datetime.now() - timedelta(days=1))
            bucket.download_if_outdated()
            return
        # If the bucket was last updated within a day nothing needs to be done.
        if latest_bucket.data_timestamp > tz_datetime.now() - timedelta(days=1):
            return

        # All other situations a new bucket should be downloaded.
        bucket = self._new_titles_bucket_file(latest_bucket.data_timestamp)
        bucket.download_if_outdated()

    # endregion Download

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        url_title_details = self._url_title_details_file(show_key).parsed()
        seasons = url_title_details.data.url_v2.node.seasons or []
        return [season.id for season in seasons]

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
            for episode in self._custom_season_episodes_file(
                season_key,
            ).parsed_episodes()
        ]

    def _media_type(self, show_key: str) -> str:
        if not self._cached_media_type:
            url_title_details = self._url_title_details_file(show_key).parsed()
            raw_media_type = url_title_details.data.url_v2.node.object_type
            self._cached_media_type = _MEDIA_TYPE_MAP[raw_media_type]
        return self._cached_media_type

    def _sources_with_offers(
        self,
        show_key: str,
    ) -> list[tuple[str, url_title_details_models.Offer]]:
        """Get all unique sources with their first corresponding offer."""
        seen: dict[str, url_title_details_models.Offer] = {}
        url_title_details = self._url_title_details_file(show_key).parsed()
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
        )
        return self.db.exec(statement)

    def minimum_new_titles_data_timestamp(self, file: NewTitles) -> datetime:
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
