# TODO: Validate
import re
from datetime import date, datetime
from itertools import chain
from typing import cast, override

from just_scrape.custom_buy_box_offers import (
    response_models as custom_buy_box_offers_models,
)
from just_scrape.url_title_details import response_models as url_title_details_models

from app.episodes.models import Episode
from app.plugins.plugins.JustWatch.files import (
    FileMixin,
    ProvidersLocale,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    @property
    def _images_base_url(self) -> str:
        """Return the base URL for images."""
        return f"https://images.{self._domain()}"

    def _format_image_url(
        self,
        url: str | None,
        profile: int = 100,
        format: str = "jpeg",
    ) -> str | None:
        """Format a JustWatch image URL with the correct base URL and profile."""
        if url is None:
            return None
        return f"{self._images_base_url}{url}".replace(
            "{profile}",
            f"s{profile}",
        ).replace("{format}", format)

    @staticmethod
    def _clean_external_url(url: str) -> str:
        """Extract the actual external URL from JustWatch's redirect wrapper."""
        match = re.search(r"r=(https?://[^&]+)", url)
        return match.group(1) if match else url

    @staticmethod
    def _find_matching_episode(
        source_key: str,
        node: custom_buy_box_offers_models.Node | url_title_details_models.Node,
    ) -> custom_buy_box_offers_models.Offer | None:
        """Find the offer that matches the source key.

        The just_scrape models split offers into separate categorized lists
        (flatrate, buy, rent, free, fast); walk them all and return the first
        item whose package short_name matches.
        """
        for item in chain(
            node.flatrate,
            node.buy,
            node.rent,
            node.free,
            node.fast,
        ):
            if item is None:
                continue
            if item.package.short_name == source_key:
                return cast("custom_buy_box_offers_models.Offer", item)
        return None

    def _sources_with_offers(  # type: ignore[override]
        self,
        show_key: str,
    ) -> list[tuple[str, custom_buy_box_offers_models.Offer]]:
        """Return (source_key, offer) pairs for all sources that have offers."""
        parsed_json = self._url_title_details_file(show_key).parsed()
        results: list[tuple[str, custom_buy_box_offers_models.Offer]] = []
        if not parsed_json.data.url_v2.node.offers:
            return results

        seen: set[str] = set()
        for offer in parsed_json.data.url_v2.node.offers:
            if offer.package.short_name not in seen:
                seen.add(offer.package.short_name)
                results.append((offer.package.short_name, offer))  # type: ignore[arg-type]

        return results

    # region Upsert Source

    def _upsert_sources(self, providers_file: ProvidersLocale) -> None:
        for provider in providers_file.parsed():
            source = Source.get_from_memory(
                self.session,
                self.plugin,
                provider["short_name"],
            )

            source = Source(
                key=provider["short_name"],
                name=provider["clear_name"],
                # The format used in this API endpoint is sligthly different than the
                # one used for other endpoints because it does not include a {format}
                # placeholder or file name. {profile}=100 and {format}=jpeg are used on
                # https://www.justwatch.com/us/new
                favicon_url=(
                    self._format_image_url(provider["icon_url"], profile=100)
                    + provider["technical_name"]
                    + ".jpeg"
                ),
                plugin_id=self.plugin.id,
            ).upsert(self.plugin, source)

            # Only use the data timestamp from the providers file for the initial
            # import. If the source already has a data_timestamp we want to keep it
            # because it will be based on data from the new titles files which are
            # more up to date.
            if not source.data_timestamp:
                source.data_timestamp = providers_file.database_record.data_timestamp

    # endregion Upsert Source

    def _upsert_shows(self, show_key: str) -> list[Show]:
        shows: list[Show] = []
        for source_key, _ in self._sources_with_offers(show_key):
            source = Source.get_one_from_memory(self.session, self.plugin, source_key)
            shows.append(self._upsert_show(source, show_key))
        return shows

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)

        parsed_json = self._url_title_details_file(show_key).parsed()
        offer = next(
            offer
            for source_key, offer in self._sources_with_offers(show_key)
            if source_key == source.key
        )
        media_type = self._media_type(show_key)
        show = Show(
            key=show_key,
            name=parsed_json.data.url_v2.node.content.title,
            media_type=media_type,
            description=parsed_json.data.url_v2.node.content.short_description,
            url=self._clean_external_url(offer.standard_web_url),
            image_url=self._images_base_url
            + parsed_json.data.url_v2.node.content.full_backdrops[0].backdrop_url,
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_seasons(show, show_key)

        self.soft_delete_missing_seasons(show_key)

        return show

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        if self._media_type(show_key) == "TV Show":
            self._upsert_show_seasons(show, show_key)
        else:
            self._upsert_movie_season(show, show_key)

    def _upsert_show_seasons(self, show: Show, show_key: str) -> None:
        # TODO: Upstream in JustScrape, add the ability to parse specific types so there
        # is less need for checking for None.
        parsed_json = self._url_title_details_file(show_key).parsed()
        seasons_data = parsed_json.data.url_v2.node.seasons
        # TODO: Eventually this should be able to be removed once JustScrape is updated.
        if seasons_data is None:
            msg = f"No seasons found for show: {show_key}"
            raise ValueError(msg)
        for season_data in seasons_data:
            existing_season = Season.get_from_memory(self.session, show, season_data.id)
            image_url = self._format_image_url(season_data.content.poster_url, 166)
            season = Season(
                image_url=image_url,
                # TODO: Should I use the other ID that matches the URL instead?
                key=season_data.id,
                sort_order=season_data.content.season_number,
                season_number=season_data.content.season_number,
                data_timestamp=self.season_data_timestamp(season_data.id, show_key),
                show_id=show.id,
            ).upsert(show, existing_season)
            self._upsert_season_episodes(show, season, season_data, show_key)
            self.soft_delete_missing_episodes(season.key)

    def _upsert_movie_season(self, show: Show, show_key: str) -> None:
        parsed_json = self._url_title_details_file(show_key).parsed()
        node_id = parsed_json.data.url_v2.node.id
        existing_season = Season.get_from_memory(self.session, show, node_id)
        season = Season(
            key=node_id,
            name="Movie",
            sort_order=0,
            data_timestamp=self.season_data_timestamp(node_id, show_key),
            show_id=show.id,
        ).upsert(show, existing_season)
        upserted_key = self._upsert_movie_episode(show, season, show_key)
        expected_keys = [upserted_key] if upserted_key else []
        season.soft_delete_missing_children(expected_keys)

    @staticmethod
    def _date_to_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return tz_datetime.combine(value, datetime.min.time())

    def _upsert_season_episodes(
        self,
        show: Show,
        season: Season,
        season_data: url_title_details_models.Season,
        show_key: str,
    ) -> None:
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
                self.session,
                season,
                season_episode.id,
            )
            episode_timestamp = self.episode_data_timestamp(
                season_episode.id,
                season.key,
                show_key,
            )
            if (
                existing_episode
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

            Episode(
                url=self._clean_external_url(episode_info.standard_web_url),
                key=season_episode.id,
                name=season_episode.content.title,
                description=season_episode.content.short_description,
                duration=season_episode.content.runtime * 60,
                sort_order=season_episode.content.episode_number,
                episode_number=season_episode.content.episode_number,
                data_timestamp=episode_timestamp,
                image_url=self._images_base_url + backdrop_image,
                release_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
                air_date=self._date_to_datetime(
                    season_episode.content.original_release_date,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

    def _upsert_movie_episode(
        self,
        show: Show,
        season: Season,
        show_key: str,
    ) -> str | None:
        source_key = show.source.key
        parsed_data = self._url_title_details_file(show_key).parsed()
        episode_info = self._find_matching_episode(
            source_key,
            parsed_data.data.url_v2.node,
        )
        if not episode_info:
            return None

        existing_episode = Episode.get_from_memory(
            self.session,
            season,
            episode_info.id,
        )
        episode_timestamp = self.episode_data_timestamp(
            episode_info.id,
            season.key,
            show_key,
        )
        if existing_episode and existing_episode.data_timestamp == episode_timestamp:
            return episode_info.id

        node = parsed_data.data.url_v2.node
        Episode(
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
            season_id=season.id,
        ).upsert(season, existing_episode)
        return episode_info.id

    # endregion Upsert
