# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from functools import cache, cached_property
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
from app.plugins.plugins.utils.base_files import JSONFile
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.ip_validator import check_ip_not_matches
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


@cache
def just_scrape_client() -> JustScrape:
    return JustScrape()


class NewTitles(JSONFile[list[new_titles_models.Edge]]):
    def __init__(self, db: Session, plugin: Plugin, source_id: str, date: date) -> None:
        self.source_id = source_id
        self.date = date
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return f"{self.source_id}/{self.date}"

    @override
    def _download(self) -> None:
        with self._log_download(f"{self.source_id} since {self.date}"):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            new_titles = just_scrape_client().new_titles
            response = new_titles.get_all_for_date(
                available_to_packages=[self.source_id],
                filter_packages=[self.source_id],
                date=self.date,
            )
            content = new_titles.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[new_titles_models.Edge]:
        new_titles = just_scrape_client().new_titles
        parsed_pages = [new_titles.parse(page) for page in raw]
        return new_titles.extract_edges(parsed_pages)


class UrlTitleDetails(JSONFile[url_title_details_models.UrlTitleDetailsResponse]):
    def __init__(self, db: Session, plugin: Plugin, show_id: str) -> None:
        self.__show_id = show_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__show_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            try:
                url_title_details = just_scrape_client().url_title_details
                response = url_title_details.get(self.__show_id)
                content = url_title_details.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid URL.
            except GraphQLError:
                self._write(None)

    @override
    def _parse(self, raw: Any) -> url_title_details_models.UrlTitleDetailsResponse:
        return just_scrape_client().url_title_details.parse(raw)


class CustomSeasonEpisodes(JSONFile[list[custom_season_episodes_models.Episode]]):
    def __init__(self, db: Session, plugin: Plugin, season_id: str) -> None:
        self.__season_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            custom_season_episodes = just_scrape_client().custom_season_episodes
            response = custom_season_episodes.get_all(node_id=self.__season_id)
            content = custom_season_episodes.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[custom_season_episodes_models.Episode]:
        custom_season_episodes = just_scrape_client().custom_season_episodes
        parsed_pages = [custom_season_episodes.parse(page) for page in raw]
        return custom_season_episodes.extract_episodes(parsed_pages)


class CustomBuyBoxOffers(
    JSONFile[custom_buy_box_offers_models.CustomBuyBoxOffersResponse],
):
    def __init__(self, db: Session, plugin: Plugin, episode_id: str) -> None:
        self.__episode_id = episode_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__episode_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__episode_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            custom_buy_box_offers = just_scrape_client().custom_buy_box_offers
            response = custom_buy_box_offers.get(self.__episode_id)
            content = custom_buy_box_offers.dump_response(response)
            self._write(content)

    @override
    def _parse(
        self,
        raw: Any,
    ) -> custom_buy_box_offers_models.CustomBuyBoxOffersResponse:
        return just_scrape_client().custom_buy_box_offers.parse(raw)


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
        self.__new_titles_files: dict[str, NewTitles] = {}
        self.__url_title_details_file: dict[str, UrlTitleDetails] = {}
        self.__custom_season_episodes_file: dict[str, CustomSeasonEpisodes] = {}
        self.__custom_buy_box_offers_file: dict[str, CustomBuyBoxOffers] = {}
        self._latest_browse_files: dict[str, NewTitles] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Cache

    def _custom_buy_box_offers_file(self, episode_id: str) -> CustomBuyBoxOffers:
        return self._get_cached_file(
            self.__custom_buy_box_offers_file,
            episode_id,
            lambda: CustomBuyBoxOffers(self.db, self.plugin, episode_id),
        )

    def _url_title_details_file(self, show_id: str) -> UrlTitleDetails:
        return self._get_cached_file(
            self.__url_title_details_file,
            show_id,
            lambda: UrlTitleDetails(self.db, self.plugin, show_id),
        )

    def _new_titles_file(self, source_id: str, date: datetime | date) -> NewTitles:
        if isinstance(date, datetime):
            date = date.date()

        cache_key = f"{source_id}_{date}"
        return self._get_cached_file(
            self.__new_titles_files,
            cache_key,
            lambda: NewTitles(self.db, self.plugin, source_id, date),
        )

    def _custom_season_episodes_file(self, season_id: str) -> CustomSeasonEpisodes:
        return self._get_cached_file(
            self.__custom_season_episodes_file,
            season_id,
            lambda: CustomSeasonEpisodes(self.db, self.plugin, season_id),
        )

    # endregion File Cache

    # region File Groups

    def _show_files(self, show_id: str) -> list[UrlTitleDetails]:
        # Movies - Required to detect changes to the show (there are no new seasons).
        # TV Show - Required to detect changes to the show and new seasons.
        return [self._url_title_details_file(show_id)]

    def _season_files(
        self,
        show_id: str,
        season_id: str,
    ) -> Sequence[UrlTitleDetails | CustomSeasonEpisodes]:
        if self._media_type == "Movie":
            # Required to detect changes to the season.
            return [self._url_title_details_file(show_id)]
        return [
            # Required to detect changes to the season.
            self._url_title_details_file(show_id),
            # Required to detect new episodes.
            self._custom_season_episodes_file(season_id),
        ]

    def _episode_files(
        self,
        season_id: str,
        episode_id: str,
    ) -> list[UrlTitleDetails | CustomSeasonEpisodes | CustomBuyBoxOffers]:
        if self._media_type == "Movie":
            # Required to detect changes to the episode.
            return [self._url_title_details_file(self._show_id)]

        return [
            # Required to detect changes to the episode.
            self._custom_season_episodes_file(season_id),
            self._custom_buy_box_offers_file(episode_id),
        ]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_id: str) -> datetime:
        return super()._show_timestamp(show_id)

    def _season_timestamp(self, show_id: str, season_id: str) -> datetime:
        return super()._season_timestamp(show_id, season_id)

    def _episode_timestamp(self, season_id: str, episode_id: str) -> datetime:
        return super()._episode_timestamp(season_id, episode_id)

    # endregion Timestamps

    # region Cached Values

    @cached_property
    def _media_type(self) -> str:
        media_type_cross_reference = {"SHOW": "TV Show", "MOVIE": "Movie"}
        url_title_details_file = self._url_title_details_file(self._show_id)
        url_title_details_data = url_title_details_file.parsed()
        raw_media_type = url_title_details_data.data.url_v2.node.object_type
        return media_type_cross_reference[raw_media_type]

    @cached_property
    def _sources_with_offers(self) -> list[tuple[str, url_title_details_models.Offer]]:
        """Get all sources with their corresponding offers."""
        result: list[tuple[str, url_title_details_models.Offer]] = []
        source_ids: set[str] = set()
        _url_title_details_json_file = self._url_title_details_file(self._show_id)
        for offer in _url_title_details_json_file.parsed().data.url_v2.node.offers:
            # If a website offers multiple different plans the data will be duplicated
            # for each plan so only use the first offer for each source.
            if offer.package.short_name in source_ids:
                continue

            result.append((offer.package.short_name, offer))
            source_ids.add(offer.package.short_name)

        return result

    @cached_property
    def __source_ids_from_file(self) -> list[str]:
        """Get all source IDs from the URL title details JSON."""
        sources_with_offers = self._sources_with_offers
        return [source_id for source_id, _ in sources_with_offers]

    @cached_property
    def __season_ids_from_file(self) -> list[str]:
        _url_title_details_file = self._url_title_details_file(self._show_id)
        seasons = _url_title_details_file.parsed().data.url_v2.node.seasons or []
        return [season.id for season in seasons]

    @cached_property
    def __episode_ids_from_file(self) -> list[str]:
        episode_ids: list[str] = []
        for season_id in self.__season_ids_from_file:
            all_season_episodes = self._custom_season_episodes_file(season_id)
            episode_ids.extend(episode.id for episode in all_season_episodes.parsed())
        return episode_ids

    # endregion Cached Values

    # region Preload

    def _preload_show_files(self, show_id: str) -> None:
        self.__preload_url_title_details(show_id)

    def _preload_season_episode_files(self, show_id: str) -> None:
        # Will be true if the user inputs an invalid URL.
        if not self._url_title_details_file(show_id).has_file_content():
            return

        if season_ids := self.__season_ids_from_file:
            self.__preload_custom_season_episodes(season_ids)
            if episode_ids := self.__episode_ids_from_file:
                self.__preload_custom_buy_box_offers(episode_ids)

    def _preload_show_season_episode_files(self, show_id: str) -> None:
        self._preload_show_files(show_id)
        self._preload_season_episode_files(show_id)

    def __preload_url_title_details(self, show_id: str) -> None:
        url_title_details_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(File.key == UrlTitleDetails.file_key(show_id))
        )
        self._add_all_to_preload_cache(url_title_details_select)

    def __preload_custom_season_episodes(self, season_ids: list[str]) -> None:
        custom_season_episodes_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        CustomSeasonEpisodes.file_key(season_id)
                        for season_id in season_ids
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(custom_season_episodes_select)

    def __preload_custom_buy_box_offers(self, episode_ids: list[str]) -> None:
        custom_buy_box_offers_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        CustomBuyBoxOffers.file_key(episode_id)
                        for episode_id in episode_ids
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(custom_buy_box_offers_select)

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
        file = self._add_one_to_preload_cache(statement)
        return self._db_file_to_new_titles_file(file)

    def _preload_all_latest_new_titles_files(self) -> None:
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

        source_keys = self.__source_ids_from_file
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

    def _download_initial_files(self) -> None:
        logger.info(f"Downloading Initial Files: {self._pretty_show_name()}")
        # Movies and TV shows both need these files.
        self.__download_initial_new_titles()
        self.__download_initial_url_title_details()

        # These files are just needed for TV shows.
        if self._media_type == "TV Show":
            self.__download_initial_custom_season_episodes()
            self.__download_initial_custom_buy_box_offers()

    def __download_initial_url_title_details(self) -> None:
        self._url_title_details_file(self._show_id)

    def __download_initial_new_titles(self) -> None:
        for source_id in self.__source_ids_from_file:
            if self._latest_browse_files.get(source_id):
                continue
            # It appears all of the dates are offset by a day for some reason so always
            # download a day in advance to get the latest files.
            initial_timestamp = tz_datetime.now()
            browse_file = self._new_titles_file(source_id, initial_timestamp)
            self._latest_browse_files[source_id] = browse_file

    def __download_initial_custom_season_episodes(self) -> None:
        for season_id in self.__season_ids_from_file:
            self._custom_season_episodes_file(season_id)

    def __download_initial_custom_buy_box_offers(self) -> None:
        for episode_id in self.__episode_ids_from_file:
            self._custom_buy_box_offers_file(episode_id)

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
