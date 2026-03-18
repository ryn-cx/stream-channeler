import re
from datetime import date, datetime, timedelta
from functools import cache
from typing import override
from urllib.parse import parse_qs, urlparse

from just_scrape.custom_buy_box_offers import (
    response_models as custom_buy_box_offers_models,
)
from just_scrape.url_title_details import response_models as url_title_details_models
from loguru import logger

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.plugins.JustWatch.files import (
    FileMixin,
    ProvidersLocale,
    UrlTitleDetails,
)
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    # region Class Methods

    @classmethod
    @cache
    def _images_base_url(cls) -> str:
        return f"https://images.{cls._domain()}"

    @classmethod
    def _clean_poster_image_url(cls, url: str) -> str:
        # 332 is the highest resolution normally used on the website it looks like for
        # season posters.
        formatted_url = url.replace("{profile}", "s332").replace("{format}", "avif")
        return cls._images_base_url() + formatted_url

    @classmethod
    def _clean_favicon_image_url(cls, url: str) -> str:
        formatted_url = url.replace("{format}", "jpeg")
        return cls._images_base_url() + formatted_url

    # endregion Class Methods

    # region Other

    @staticmethod
    def _clean_external_url(url: str) -> str:
        """Remove affiliate tracking from the episode URL."""
        parsed_url = urlparse(url)

        # Used by Crunchyroll and potentially others.
        if re.compile(r"^https:\/\/[a-z]+\.pxf\.io\/").match(url):
            query_params = parse_qs(parsed_url.query)
            if redirect_url := query_params.get("u"):
                url = redirect_url[0]
        return url

    # TODO: What are FastItem entries?
    def _find_matching_episode(
        self,
        source_key: str,
        custom_buy_box_offers: custom_buy_box_offers_models.Node,
    ) -> (
        custom_buy_box_offers_models.FlatrateItem
        | custom_buy_box_offers_models.BuyItem
        | custom_buy_box_offers_models.FreeItem
        | custom_buy_box_offers_models.FastItem
        # TODO: Enable rent items once the data structure exists.
        # | custom_buy_box_offers_models.RentItem
        | None
    ):
        # Eventually the types here will no longer have unknown values so the type
        # errors will go away as JustScrape automatically updates.
        offers: list[
            custom_buy_box_offers_models.FlatrateItem
            | custom_buy_box_offers_models.BuyItem
            | custom_buy_box_offers_models.FreeItem
            | custom_buy_box_offers_models.FastItem
        ] = []
        if custom_buy_box_offers.flatrate:
            offers.extend(custom_buy_box_offers.flatrate)

        if custom_buy_box_offers.buy:
            offers.extend(custom_buy_box_offers.buy)

        if custom_buy_box_offers.rent:
            offers.extend(custom_buy_box_offers.rent)

        if custom_buy_box_offers.free:
            offers.extend(custom_buy_box_offers.free)

        if custom_buy_box_offers.fast:
            offers.extend(custom_buy_box_offers.fast)

        for offer in offers:
            if not offer.package:
                msg = "Offer package is None, which shouldn't happen."
                raise ValueError(msg)
            if offer.package.short_name == source_key:
                return offer

        return None

    def _get_best_episode_date(
        self,
        episode_data: UrlTitleDetails,
    ) -> datetime | None:
        """Get the best available date for the episode."""
        if (
            release_date
            := episode_data.parsed().data.url_v2.node.content.original_release_date
        ):
            return datetime.combine(release_date, datetime.min.time())

        # When the year is not known a value of 0 is returned for shows, this is
        # PROBABLY also true for movies. If the value is 0 None is returned.
        if year := episode_data.parsed().data.url_v2.node.content.original_release_year:
            return tz_datetime(year, 1, 1)
        return None

    # endregion Other

    # region Upsert

    def initialize_plugin(self) -> None:
        """Download the providers locale file and update the plugin's data_timestamp."""
        if self.plugin.data_timestamp is None:
            # TODO: Periodic updates of the providers.
            providers_file = self._providers_locale_file()
            providers_file.download_if_outdated()
            self._download_initial_new_titles_bucket()
            self._upsert_sources(providers_file)
            self.plugin.data_timestamp = providers_file.database_entry.data_timestamp
            self.plugin.set_update_at(self.plugin.data_timestamp + timedelta(days=1))

    def _upsert_sources(self, providers_file: ProvidersLocale) -> None:
        """Upsert all providers from the providers locale file as sources."""
        _cache = self._preload_sources()
        for provider in providers_file.parsed():
            source = Source.get_from_memory(
                self.db,
                self.plugin,
                provider["short_name"],
            )
            data_timestamp = providers_file.database_entry.data_timestamp
            source = SourceInput(
                key=provider["short_name"],
                name=provider["clear_name"],
                data_timestamp=data_timestamp,
            ).upsert(self.plugin, source)

    def _upsert_shows(self, show_key: str) -> list[Show]:
        """Upsert all sources and their shows from the URL title details JSON."""
        shows: list[Show] = []
        for source_key, _ in self._sources_with_offers(show_key):
            source = Source.get_one_from_memory(self.db, self.plugin, source_key)
            shows.append(self._upsert_show(source, show_key))
        return shows

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.db, source, show_key)
        show_timestamp = self._newest_file_timestamp(self._show_files(show_key))

        if force_reimport or not show or show.data_timestamp != show_timestamp:
            logger.info(f"Upserting show: {self._pretty_show_name(show_key)}")
            parsed_json = self._url_title_details_file(show_key).parsed()
            offer = next(
                offer
                for source_key, offer in self._sources_with_offers(show_key)
                if source_key == source.key
            )
            show = ShowInput(
                key=show_key,
                name=parsed_json.data.url_v2.node.content.title,
                media_type=self._media_type(show_key),
                description=parsed_json.data.url_v2.node.content.short_description,
                url=self._clean_external_url(offer.standard_web_url),
                image_url=self._images_base_url()
                + parsed_json.data.url_v2.node.content.full_backdrops[0].backdrop_url,
                data_timestamp=show_timestamp,
            ).upsert(source, show)

        self._upsert_seasons(show, show_key, force_reimport=force_reimport)
        return show

    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        season_keys = self._season_keys_from_file(show_key)
        show.soft_delete_missing_children(season_keys)
        if self._media_type(show_key) == "TV Show":
            self._upsert_show_seasons(show, show_key, force_reimport=force_reimport)
        else:
            self._upsert_movie_season(show, show_key, force_reimport=force_reimport)

    def _upsert_show_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        # TODO: Upstream in JustScrape, add the ability to parse specific types so there
        # is less need for checking for None.
        parsed_json = self._url_title_details_file(show_key).parsed()
        seasons_data = parsed_json.data.url_v2.node.seasons
        # TODO: Eventually this should be able to be removed once JustScrape is updated.
        if seasons_data is None:
            msg = f"No seasons found for show: {show_key}"
            raise ValueError(msg)
        for season_data in seasons_data:
            season = Season.get_from_memory(self.db, show, season_data.id)
            season_timestamp = self._newest_file_timestamp(
                self._season_files(season_data.id, show_key),
            )
            if (
                force_reimport
                or not season
                or season.data_timestamp != season_timestamp
            ):
                logger.info(f"Upserting season: {season_data.id}")
                season = SeasonInput(
                    image_url=self._clean_poster_image_url(
                        season_data.content.poster_url,
                    ),
                    # TODO: Should I use the other ID that matches the URL instead?
                    key=season_data.id,
                    sort_order=season_data.content.season_number,
                    season_number=season_data.content.season_number,
                    data_timestamp=season_timestamp,
                ).upsert(show, season)
            self._upsert_season_episodes(
                show,
                season,
                season_data,
                show_key,
                force_reimport=force_reimport,
            )

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        parsed_json = self._url_title_details_file(show_key).parsed()
        node_id = parsed_json.data.url_v2.node.id
        season = Season.get_from_memory(self.db, show, node_id)
        season_timestamp = self._newest_file_timestamp(
            self._season_files(node_id, show_key),
        )
        if force_reimport or not season or season.data_timestamp != season_timestamp:
            logger.info(f"Upserting season: {node_id}")
            season = SeasonInput(
                key=node_id,
                name="Movie",
                sort_order=0,
                data_timestamp=season_timestamp,
            ).upsert(show, season)
        self._upsert_movie_episode(
            show,
            season,
            show_key,
            force_reimport=force_reimport,
        )

    @staticmethod
    def _date_to_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, datetime.min.time())

    def _upsert_season_episodes(
        self,
        show: Show,
        season: Season,
        season_data: url_title_details_models.Season,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        episode_keys = self._episode_keys_from_file(season_data.id)
        season.soft_delete_missing_children(episode_keys)

        source_key = show.source.key
        custom_season_episodes_file = self._custom_season_episodes_file(
            season_data.id,
        )
        backdrops = (
            self._url_title_details_file(show_key)
            .parsed()
            .data.url_v2.node.content.full_backdrops
        )
        for i, season_episode in enumerate(
            custom_season_episodes_file.parsed_episodes(),
        ):
            existing_episode = Episode.get_from_memory(
                self.db,
                season,
                season_episode.id,
            )
            # Each episode has its own CustomBuyBoxOffers file so the timestamp
            # must be computed per-episode.
            episode_timestamp = self._newest_file_timestamp(
                self._episode_files(
                    season_episode.id,
                    season.key,
                    show_key=show_key,
                ),
            )
            if (
                not force_reimport
                and existing_episode
                and existing_episode.data_timestamp == episode_timestamp
            ):
                continue

            buy_box_offers = self._custom_buy_box_offers_file(season_episode.id)
            episode_info = self._find_matching_episode(
                source_key,
                buy_box_offers.parsed().data.node,
            )
            if not episode_info:
                continue

            # For a little bit of variety in the images, rotate through the backdrop
            # images so every episode doesn't have the same image.
            backdrop_image = backdrops[i % len(backdrops)].backdrop_url

            EpisodeInput(
                url=self._clean_external_url(episode_info.standard_web_url),
                key=season_episode.id,
                name=season_episode.content.title,
                description=season_episode.content.short_description,
                duration=season_episode.content.runtime * 60,
                sort_order=season_episode.content.episode_number,
                episode_number=season_episode.content.episode_number,
                data_timestamp=episode_timestamp,
                image_url=self._images_base_url() + backdrop_image,
                release_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
                air_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
            ).upsert(season, existing_episode)

    def _upsert_movie_episode(
        self,
        show: Show,
        season: Season,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        source_key = show.source.key
        parsed_data = self._url_title_details_file(show_key).parsed()
        episode_info = self._find_matching_episode(
            source_key,
            parsed_data.data.url_v2.node,
        )
        if not episode_info:
            return

        episode_timestamp = self._newest_file_timestamp(
            self._episode_files(episode_info.id, season.key, show_key=show_key),
        )
        existing_episode = Episode.get_from_memory(
            self.db,
            season,
            episode_info.id,
        )
        if (
            not force_reimport
            and existing_episode
            and existing_episode.data_timestamp == episode_timestamp
        ):
            return

        node = parsed_data.data.url_v2.node
        logger.info(f"Upserting episode: {node.content.title}")
        EpisodeInput(
            url=self._clean_external_url(episode_info.standard_web_url),
            key=episode_info.id,
            name=node.content.title,
            description=node.content.short_description,
            duration=node.content.runtime * 60,
            sort_order=0,
            episode_number=0,
            data_timestamp=episode_timestamp,
            release_date=self._date_to_datetime(node.content.original_release_date),
            air_date=self._date_to_datetime(node.content.original_release_date),
        ).upsert(season, existing_episode)

    # endregion Upsert
