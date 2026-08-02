# TODO: Validate
import re
from datetime import date, datetime
from itertools import chain
from typing import Literal, cast, override

from just_scrape.custom_buy_box_offers import (
    models as custom_buy_box_offers_models,
)
from just_scrape.url_title_details import models as url_title_details_models

from app.shows.models import Show
from app.utils import tz_datetime
from plugins.JustWatch.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @classmethod
    @override
    def _domain(cls) -> str:
        return "justwatch.com"

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        details_file = self.url_title_details_file(show_key)
        details_file.download_if_outdated()
        content = details_file.parsed().data.url_v2.node.content
        return self._tmdb_search_media(
            content.title,
            self._tmdb_media_type(show_key),
            content.original_release_year,
        )

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._media_type(show_key) == "Movie" else "tv"

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        seasons = (
            self.url_title_details_file(show_key).parsed().data.url_v2.node.seasons
        )
        if seasons is None:
            return None
        for season in seasons:
            if season.id == season_key:
                return season.content.season_number
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        episodes = self.custom_season_episodes_file(season_key).parsed_episodes()
        for episode in episodes:
            if episode.id == episode_key:
                return episode.content.episode_number
        return None

    @property
    def _images_base_url(self) -> str:
        """Return the base URL for images."""
        return f"https://images.{self._domain()}"

    def _format_image_url(
        self,
        url: str | None,
        profile: int = 100,
        image_format: str = "jpeg",
    ) -> str | None:
        """Format a JustWatch image URL with the correct base URL and profile."""
        if url is None:
            return None
        return f"{self._images_base_url}{url}".replace(
            "{profile}",
            f"s{profile}",
        ).replace("{format}", image_format)

    def _favicon_url(self, provider: dict[str, str]) -> str | None:
        icon_url = self._format_image_url(provider["icon_url"], profile=100)
        if icon_url is None:
            return None
        return f"{icon_url}/{provider['technical_name']}.avif"

    @staticmethod
    def _clean_external_url(url: str) -> str:
        """Extract the actual external URL from JustWatch's redirect wrapper."""
        match = re.search(r"r=(https?://[^&]+)", url)
        return match.group(1) if match else url

    @staticmethod
    def _date_to_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return tz_datetime.combine(value, datetime.min.time())

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
