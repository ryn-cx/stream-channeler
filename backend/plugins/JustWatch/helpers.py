# TODO: Validate
from datetime import date, datetime
from itertools import chain
from typing import cast, override
from urllib.parse import parse_qs, urlsplit

from just_scrape.buy_box_offers import models as buy_box_offers_models
from just_scrape.url_title_details import models as url_title_details_models

from app.media.media_type import MediaType
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.JustWatch.files import FileMixin
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import sorted_plugins

# The query parameters an affiliate link hides its destination behind. `u` is
# what Impact Radius (`*.pxf.io`) uses; `r` is the older shape.
_REDIRECT_PARAMETERS = ("u", "r")


class HelperMixin(FileMixin, register=False):
    @classmethod
    @override
    def _domain(cls) -> str:
        return "justwatch.com"

    @classmethod
    def _plugin_for_url(cls, url: str) -> type[AbstractPlugin] | None:
        """Return the plugin that imports `url` itself, if there is one."""
        for plugin_class in sorted_plugins():
            if (
                plugin_class is not cls
                and plugin_class.implements("import_url")
                and plugin_class.is_valid_url_format(url)
            ):
                return plugin_class
        return None

    def _plugin_for_source(
        self,
        show_key: str,
        source_key: str,
    ) -> type[AbstractPlugin] | None:
        """Return the plugin that owns the title's media on `source_key`."""
        for offer_source_key, offer in self._sources_with_offers(show_key):
            if offer_source_key == source_key:
                offer_url = self._clean_external_url(offer.standard_web_url)
                return self._plugin_for_url(offer_url)
        return None

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
            self.tmdb_media_type(show_key),
            content.original_release_year,
        )

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return (
            MediaType.movie if self._media_type(show_key) == "Movie" else MediaType.tv
        )

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
        episodes = self.season_episodes_file(season_key).parsed_episodes()
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
        """Return the URL a JustWatch offer actually points at.

        An offer is an affiliate link that carries the real destination in a
        query parameter, percent-encoded
        (`crunchyroll.pxf.io/xk92Nv?u=https%3A%2F%2Fwww.crunchyroll.com%2F...`).
        The service's own plugin only recognises the URL once it has been
        unwrapped, and the wrapper is no use as a stored `url` either.
        """
        parameters = parse_qs(urlsplit(url).query)
        for name in _REDIRECT_PARAMETERS:
            for value in parameters.get(name, ()):
                if value.startswith(("http://", "https://")):
                    return value
        return url

    @staticmethod
    def _date_to_datetime(value: date | None) -> datetime | None:
        if value is None:
            return None
        return tz_datetime.combine(value, datetime.min.time())

    @staticmethod
    def _find_matching_episode(
        source_key: str,
        node: buy_box_offers_models.Node | url_title_details_models.Node,
    ) -> buy_box_offers_models.Offer | None:
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
                return cast("buy_box_offers_models.Offer", item)
        return None
