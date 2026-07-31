# TODO: Validate
"""JustWatch plugin."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.utils import tz_datetime
from plugins.JustWatch.files import LOOKUP_ONLY_MESSAGE, FileMixin
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.manage_plugins import sorted_plugins

if TYPE_CHECKING:
    from just_scrape.url_title_details.models import Node

    from app.episodes.models import Episode
    from app.plugins.models import Plugin
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source

_DETAILS_MAX_AGE = timedelta(days=30)

# Only the offers that make a title watchable on a subscription, free, or
# ad-supported service. Buy and rent offers are purchase links, not places the
# title can be streamed.
_AVAILABLE_MONETIZATION_TYPES = (
    "FLATRATE",
    "FLATRATE_AND_BUY",
    "FREE",
    "ADS",
    "FAST",
)

_URL_REGEX = r"(\/[a-z]{2}\/(?:movie|tv-show)\/[^?#]+?)\/?(?:[?#].*)?$"


class JustWatch(FileMixin, register=True):
    """JustWatch plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.justwatch.com/favicon.ico"

    # JustWatch only points at other services, so it needs a `Plugin` record for
    # its files but never a `Source` of its own.
    @override
    def initialize_source(self) -> None:
        return

    @classmethod
    @override
    def _domain(cls) -> str:
        return "justwatch.com"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        return cls._domain_regex() + _URL_REGEX

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "Imports a title from every other plugin that has it, based on where "
            "JustWatch says it is available to stream.\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.justwatch.com/us/movie/megamind`\n\n"
            "> [!TIP/Show]\n"
            "> `https://www.justwatch.com/us/tv-show/scooby-doo-where-are-you`\n\n"
            "> [!TIP/Season]\n"
            "> `https://www.justwatch.com/us/tv-show/strip-law/season-1`\n\n"
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        details_file = self.url_title_details_file(self._full_path(url))
        details_file.download_if_outdated(tz_datetime.now() - _DETAILS_MAX_AGE)
        if not details_file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)

        results: list[URLImportResult] = []
        for offer_url in self._offer_urls(details_file.parsed().data.url_v2.node):
            plugin_class = self._plugin_for_url(offer_url)
            if plugin_class:
                results.extend(plugin_class(self.session).import_url(offer_url))
        return results

    @classmethod
    def _full_path(cls, url: str) -> str:
        """Return the JustWatch path that identifies the title in `url`."""
        match = re.match(cls._url_regex(), url)
        if not match:
            msg = f"Invalid {cls.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
        return match.group(1).removeprefix("/")

    @staticmethod
    def _offer_urls(node: Node) -> list[str]:
        """Return the URL of every service the title can be streamed on."""
        offer_urls: list[str] = []
        for offer in node.offers:
            if (
                offer.monetization_type in _AVAILABLE_MONETIZATION_TYPES
                and offer.standard_web_url not in offer_urls
            ):
                offer_urls.append(offer.standard_web_url)
        return offer_urls

    @classmethod
    def _plugin_for_url(cls, url: str) -> type[AbstractPlugin] | None:
        """Return the plugin that can import `url`, if there is one."""
        for plugin_class in sorted_plugins():
            if (
                plugin_class is not cls
                and plugin_class.implements("import_url")
                and plugin_class.is_valid_url_format(url)
            ):
                return plugin_class
        return None

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_source(self, source: Source) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_season(self, season: Season) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_episode(self, episode: Episode) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)
