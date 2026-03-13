# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any, override

from just_scrape import JustScrape
from just_scrape.custom_buy_box_offers import (
    response_models as custom_buy_box_offers_models,
)
from just_scrape.custom_season_episodes import (
    response_models as custom_season_episodes_models,
)
from just_scrape.exceptions import GraphQLError
from just_scrape.new_titles import response_models as new_titles_models
from just_scrape.url_title_details import response_models as url_title_details_models
from loguru import logger
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_plugin import BasePlugin, JSONFile
from app.plugins.plugins.utils.base_plugin.files import GAPIJSON
from app.plugins.plugins.utils.ip_validator import check_ip_not_matches
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


def just_scrape_client() -> JustScrape:
    return JustScrape()


class NewTitles(JSONFile[list[new_titles_models.Edge]]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        source_key: str,
        date: date,
    ) -> None:
        self.source_key = source_key
        self.date = date
        self.unique_identifier = f"{source_key}/{date}"
        super().__init__(db, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(f"{self.source_key} since {self.date}"):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            new_titles = just_scrape_client().new_titles
            response = new_titles.get_all_for_date(
                available_to_packages=[self.source_key],
                filter_packages=[self.source_key],
                date=self.date,
            )
            content = new_titles.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[new_titles_models.Edge]:
        new_titles = just_scrape_client().new_titles
        parsed_pages = [new_titles.parse(page) for page in raw]
        return new_titles.extract_edges(parsed_pages)


class UrlTitleDetails(GAPIJSON[url_title_details_models.UrlTitleDetailsResponse]):
    api_endpoint = just_scrape_client().url_title_details

    def __init__(self, db: Session, plugin: Plugin, show_key: str) -> None:
        self.unique_identifier = show_key
        super().__init__(db, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            try:
                response = self._get()
                content = self.api_endpoint.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid URL.
            except GraphQLError:
                self._write(None)


class CustomSeasonEpisodes(JSONFile[list[custom_season_episodes_models.Episode]]):
    def __init__(self, db: Session, plugin: Plugin, season_key: str) -> None:
        self.__season_key = season_key
        self.unique_identifier = season_key
        super().__init__(db, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            custom_season_episodes = just_scrape_client().custom_season_episodes
            response = custom_season_episodes.get_all(node_id=self.__season_key)
            content = custom_season_episodes.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[custom_season_episodes_models.Episode]:
        custom_season_episodes = just_scrape_client().custom_season_episodes
        parsed_pages = [custom_season_episodes.parse(page) for page in raw]
        return custom_season_episodes.extract_episodes(parsed_pages)


class CustomBuyBoxOffers(
    GAPIJSON[custom_buy_box_offers_models.CustomBuyBoxOffersResponse],
):
    api_endpoint = just_scrape_client().custom_buy_box_offers

    def __init__(self, db: Session, plugin: Plugin, episode_key: str) -> None:
        self.unique_identifier = episode_key
        super().__init__(db, plugin)


class FileMixin(BasePlugin, register=False):
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
        self._latest_browse_files: dict[str, NewTitles] = {}
        self.__media_type_cache: dict[str, str] = {}
        self.__sources_with_offers_cache: dict[
            str,
            list[tuple[str, url_title_details_models.Offer]],
        ] = {}
        self.__source_keys_cache: dict[str, list[str]] = {}
        self.__season_keys_cache: dict[str, list[str]] = {}
        self.__episode_keys_cache: dict[str, list[str]] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Cache

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

    # endregion File Cache

    # region File Groups

    def _show_files(self, show_key: str) -> list[UrlTitleDetails]:
        # Movies - Required to detect changes to the show (there are no new seasons).
        # TV Show - Required to detect changes to the show and new seasons.
        return [self._url_title_details_file(show_key)]

    def _season_files(
        self,
        show_key: str,
        season_key: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the season.
            return [self._url_title_details_file(show_key)]
        return [
            # Required to detect changes to the season.
            self._url_title_details_file(show_key),
            # Required to detect new episodes.
            self._custom_season_episodes_file(season_key),
        ]

    def _episode_files(
        self,
        season_key: str,
        episode_key: str,
        *,
        show_key: str = "",
    ) -> list[UrlTitleDetails | CustomSeasonEpisodes | CustomBuyBoxOffers]:
        if self._media_type(show_key) == "Movie":
            # Required to detect changes to the episode.
            return [self._url_title_details_file(show_key)]

        return [
            # Required to detect changes to the episode.
            self._custom_season_episodes_file(season_key),
            self._custom_buy_box_offers_file(episode_key),
        ]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_key: str) -> datetime:
        return super()._show_timestamp(show_key)

    def _season_timestamp(self, show_key: str, season_key: str) -> datetime:
        return super()._season_timestamp(show_key, season_key)

    def _episode_timestamp(self, season_key: str, episode_key: str) -> datetime:
        return super()._episode_timestamp(season_key, episode_key)

    # endregion Timestamps

    # region Cached Values

    def _media_type(self, show_key: str) -> str:
        if show_key not in self.__media_type_cache:
            media_type_cross_reference = {"SHOW": "TV Show", "MOVIE": "Movie"}
            url_title_details_file = self._url_title_details_file(show_key)
            url_title_details_data = url_title_details_file.parsed()
            raw_media_type = url_title_details_data.data.url_v2.node.object_type
            self.__media_type_cache[show_key] = media_type_cross_reference[
                raw_media_type
            ]
        return self.__media_type_cache[show_key]

    def _sources_with_offers(
        self,
        show_key: str,
    ) -> list[tuple[str, url_title_details_models.Offer]]:
        """Get all sources with their corresponding offers."""
        if show_key not in self.__sources_with_offers_cache:
            result: list[tuple[str, url_title_details_models.Offer]] = []
            source_keys: set[str] = set()
            _url_title_details_json_file = self._url_title_details_file(show_key)
            for offer in _url_title_details_json_file.parsed().data.url_v2.node.offers:
                # If a website offers multiple different plans the data will be duplicated
                # for each plan so only use the first offer for each source.
                if offer.package.short_name in source_keys:
                    continue

                result.append((offer.package.short_name, offer))
                source_keys.add(offer.package.short_name)
            self.__sources_with_offers_cache[show_key] = result
        return self.__sources_with_offers_cache[show_key]

    def _source_keys_from_file(self, show_key: str) -> list[str]:
        """Get all source IDs from the URL title details JSON."""
        if show_key not in self.__source_keys_cache:
            self.__source_keys_cache[show_key] = [
                source_key for source_key, _ in self._sources_with_offers(show_key)
            ]
        return self.__source_keys_cache[show_key]

    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if show_key not in self.__season_keys_cache:
            _url_title_details_file = self._url_title_details_file(show_key)
            seasons = _url_title_details_file.parsed().data.url_v2.node.seasons or []
            self.__season_keys_cache[show_key] = [season.id for season in seasons]
        return self.__season_keys_cache[show_key]

    def _episode_keys_from_file(self, show_key: str) -> list[str]:
        if show_key not in self.__episode_keys_cache:
            episode_keys: list[str] = []
            for season_key in self._season_keys_from_file(show_key):
                all_season_episodes = self._custom_season_episodes_file(season_key)
                episode_keys.extend(
                    episode.id for episode in all_season_episodes.parsed()
                )
            self.__episode_keys_cache[show_key] = episode_keys
        return self.__episode_keys_cache[show_key]

    # endregion Cached Values

    # region Preload

    def _preload_show_files(self, show_key: str) -> None:
        self.__preload_url_title_details(show_key)

    def _preload_season_episode_files(self, show_key: str) -> None:
        # Will be true if the user inputs an invalid URL.
        if not self._url_title_details_file(show_key).database_entry.content:
            return

        if season_keys := self._season_keys_from_file(show_key):
            self.__preload_custom_season_episodes(season_keys)
            if episode_keys := self._episode_keys_from_file(show_key):
                self.__preload_custom_buy_box_offers(episode_keys)

    def _preload_show_season_episode_files(self, show_key: str) -> None:
        self._preload_show_files(show_key)
        self._preload_season_episode_files(show_key)

    def __preload_url_title_details(self, show_key: str) -> None:
        url_title_details_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(File.key == self._url_title_details_file(show_key).file_key())
        )
        self.db.exec(url_title_details_select).all()

    def __preload_custom_season_episodes(self, season_keys: list[str]) -> None:
        custom_season_episodes_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        self._custom_season_episodes_file(season_key).file_key()
                        for season_key in season_keys
                    ],
                ),
            )
        )
        self.db.exec(custom_season_episodes_select).all()

    def __preload_custom_buy_box_offers(self, episode_keys: list[str]) -> None:
        custom_buy_box_offers_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        self._custom_buy_box_offers_file(episode_key).file_key()
                        for episode_key in episode_keys
                    ],
                ),
            )
        )
        self.db.exec(custom_buy_box_offers_select).all()

    def _preload_latest_new_titles_file(self, source_key: str) -> NewTitles:
        """Preload the latest NewTitles file for the given source."""
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitles.__name__}/{source_key}"),
            )
            .order_by(col(File.data_timestamp).desc())
            .limit(1)
        )
        file = self.db.exec(statement).first()
        return self._db_file_to_new_titles_file(file)

    def _preload_all_latest_new_titles_files(self, show_key: str) -> None:
        # TODO: This is implemented in a kind of terrible way, it gets the latest 1000
        # GetNewTitles files and just hopes that every source will be contained in that
        # set.
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitles.__name__}/"),
                col(File.extra).is_(None),
            )
            .order_by(col(File.data_timestamp).desc())
            .limit(1000)
        )

        source_keys = self._source_keys_from_file(show_key)
        for file in self.db.exec(statement).all():
            source_key = file.key.split("/")[1]
            if source_key not in source_keys or source_key in self._latest_browse_files:
                continue
            self._latest_browse_files[source_key] = self._db_file_to_new_titles_file(
                file,
            )

            # Stop early if all sources have been found.
            if len(self._latest_browse_files) == len(source_keys):
                break

    # endregion Preload

    def _db_file_to_new_titles_file(self, file: File) -> NewTitles:
        # TODO: This feels inefficient
        split_file = file.key.split("/")
        source_key = split_file[1]
        file_id_str = NewTitles.file_key_to_unique_identifier(split_file[-1])
        file_id_date = tz_datetime.fromisotimestamp(file_id_str)
        return self._new_titles_file(source_key, file_id_date)

    # region Download

    def _download_show_files(self, show_key: str) -> None:
        logger.info(f"Downloading Initial Files: {self._pretty_show_name(show_key)}")
        # Movies and TV shows both need these files.
        self.__download_initial_new_titles(show_key)
        self.__download_initial_url_title_details(show_key)

        # These files are just needed for TV shows.
        if self._media_type(show_key) == "TV Show":
            self.__download_initial_custom_season_episodes(show_key)
            self.__download_initial_custom_buy_box_offers(show_key)

    def __download_initial_url_title_details(self, show_key: str) -> None:
        self._url_title_details_file(show_key)

    def __download_initial_new_titles(self, show_key: str) -> None:
        for source_key in self._source_keys_from_file(show_key):
            if self._latest_browse_files.get(source_key):
                continue
            # It appears all of the dates are offset by a day for some reason so always
            # download a day in advance to get the latest files.
            initial_timestamp = tz_datetime.now()
            browse_file = self._new_titles_file(source_key, initial_timestamp)
            self._latest_browse_files[source_key] = browse_file

    def __download_initial_custom_season_episodes(self, show_key: str) -> None:
        for season_key in self._season_keys_from_file(show_key):
            self._custom_season_episodes_file(season_key)

    def __download_initial_custom_buy_box_offers(self, show_key: str) -> None:
        for episode_key in self._episode_keys_from_file(show_key):
            self._custom_buy_box_offers_file(episode_key)

    def _download_missing_new_titles_files(self, source: Source) -> None:
        latest_file = self._latest_browse_files[source.key]
        # JustWatch works by downloading the files for a single day into a file. This
        # means that a file needs to exist for every single day. The date in the file
        # name represents all new episodes for that specific date and the data_timestamp
        # is when the file was downloaded.
        last_download_date = latest_file.date
        # It appears all of the dates are offset by a day for some reason so always
        # download a day in advance to get the latest files.
        current_date = tz_datetime.now().date() + timedelta(days=1)
        while last_download_date < current_date:
            self._new_titles_file(source.key, last_download_date)
            last_download_date += timedelta(days=1)

    def _download_outdated_new_titles_files(self, source: Source) -> None:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{NewTitles.__name__}/{source.key}"),
                col(File.extra).is_(None),
            )
            .order_by(col(File.data_timestamp).desc())
        )

        for file in self.db.exec(statement).all():
            # Every file should be downloaded at least 2 days after the date to make
            # sure no values are missed. 1 day of buffer due to possible timezone
            # differences and anothr 24 hours to make sure all data for the specific
            # date is included.
            new_titles_file = self._db_file_to_new_titles_file(file)
            file_datetime = tz_datetime.combine(
                new_titles_file.date,
                datetime.min.time(),
            )
            new_titles_file.download_if_outdated(file_datetime + timedelta(days=2))

    # endregion Download
