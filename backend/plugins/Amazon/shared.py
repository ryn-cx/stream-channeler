"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

import re
from abc import ABC
from functools import cached_property
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import func
from sqlmodel import col, select

from app.sources.models import Source
from app.titles.models import Title
from app.users.service.accounts import get_or_create_automatic_channel_user
from app.utils import tz_datetime
from app.watch_providers.models import WatchProvider
from plugins.Amazon.constants import (
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
)
from plugins.Amazon.files import Detail
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.users.models import User
    from plugins.utils.abstract_plugin import URLImportResult


class AmazonShared(BasePlugin):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon"

    @classmethod
    @override
    def source_name(cls) -> str:
        raise NotImplementedError

    @property
    @override
    def source(self) -> Source:
        raise NotImplementedError

    @cached_property
    @override
    def automatic_channel_user(self) -> User:
        return get_or_create_automatic_channel_user(self.session, self.plugin_name())

    @override
    def _channel_name(self, topic_prefix: str) -> str:
        return f"{topic_prefix} on {self.plugin_name()}"

    @override
    def _channel_description(self, topic_prefix: str) -> str:
        return (
            f"All {topic_prefix.removeprefix('All ')} titles on {self.plugin_name()}."
            "\n\nThis is an automatically generated channel based on the titles that "
            "have been imported by all of Stream Channeler's users."
        )

    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        # This is just the names that do not fall under the "XXX Amazon Channel" format,
        # those names are checked in matches_tmdb_provider.
        return (
            "Amazon Prime Video",
            "Amazon Prime Video Free with Ads",
            "Amazon Prime Video with Ads",
            "Amazon Video",
        )

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (
            "Amazon Prime",
            "Free on Amazon",
            "Purchase on Amazon",
            "Unavailable on Amazon",
        )

    @classmethod
    @override
    def _domains(cls) -> list[str]:
        return ["primevideo.com", "amazon.com"]

    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.casefold().endswith("amazon channel")

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX)

    def link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX):
            if match := re.match(domain_regex + url_regex, url):
                return match.group("link_id")

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def title_key_from_url(self, url: str) -> str:
        # link_id is the id inside of the URL, this URL may point to a season so it
        # needs to be downloaded and parsed to get the actual title key.
        link_id = self.link_id_from_url(url)
        detail_file = self.detail_file(link_id)
        if detail_file.does_not_exist():
            detail_file.download_if_outdated()
        return detail_file.parsed().title_key

    def detail_file(self, link_id: str) -> Detail:
        return self._cached_file(Detail, link_id)

    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Detects changes to the title and new seasons.
        return [self.detail_file(title_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Detect changes to the episode.
        return self._season_files(season_key, title_key)


class AmazonImporterChannels(AmazonShared, BaseImporter, ABC):
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        parsed = self.detail_file(title.key).parsed()
        channel_keys: list[str] = ["All Titles"]
        if parsed.purchasable:
            channel_keys.append("Purchase")
        channel_keys.extend(parsed.genres)
        channel_keys.extend(parsed.studios)
        channel_keys.extend(
            f"{audio_track} Audio" for audio_track in parsed.audio_tracks
        )
        channel_keys.extend(f"{subtitle} Subtitles" for subtitle in parsed.subtitles)

        for channel_key in dict.fromkeys(channel_keys):
            self.add_new_urls_to_channel(channel_key, [title.url])

    def add_other_titles_on_page_to_channels(self, title: Title) -> None:
        title_urls = self.detail_file(title.key).other_title_urls_on_this_page()
        self.add_new_urls_to_channel("All Titles", title_urls)


class AmazonImporterUpsert(AmazonImporterChannels, ABC):
    def _get_or_create_source(self, source_key: str) -> Source:
        """Get or create a source if it doesn't already exist."""
        if existing_source := Source.get(self.session, self.plugin, source_key):
            return existing_source

        return Source(
            key=source_key,
            favicon_url=self._source_favicon_url(source_key),
            link_to_tmdb=self._link_to_tmdb(),
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
            update_at=self._next_source_update_at(),
        ).upsert(self.plugin, None)

    # TODO: Validate
    def title_sources(self, title_key: str) -> list[Source]:
        """Return every `Source` a `Title` belongs to."""
        parsed = self.detail_file(title_key).parsed()
        sources = [
            self._get_or_create_source(f"{channel.name} on Amazon")
            for channel in parsed.channels
        ]
        if parsed.included_with_prime:
            sources.append(self._sources["Amazon Prime"])
        if parsed.free_with_ads:
            sources.append(self._sources["Free on Amazon"])
        if parsed.purchasable:
            sources.append(self._sources["Purchase on Amazon"])
        # Unwatchable titles are added
        return sources or [self._sources["Unavailable on Amazon"]]

    # TODO: Validate
    def _subscription_id(self, source: Source, title_key: str) -> str | None:
        # freewithads are the awful names Amazon uses internally for subscription
        # identification.
        if source.key == "Amazon Prime":
            return "Prime"
        if source.key == "Free on Amazon":
            return "freewithads"
        return next(
            (
                channel.subscription_id
                for channel in self.detail_file(title_key).parsed().channels
                if f"{channel.name} on Amazon" == source.key
            ),
            None,
        )

    # TODO: This is a mess
    def _source_favicon_url(self, source_key: str) -> str:
        channel_name = source_key.removesuffix(" on Amazon")
        downcased = func.lower(col(WatchProvider.name))
        simple_provider_name = func.regexp_replace(downcased, "[^a-z0-9]", "", "g")
        for name in (f"{channel_name} Amazon Channel", channel_name):
            comparable_name = re.sub(r"[^a-z0-9]", "", name.lower())
            statement = select(WatchProvider.logo_url).where(
                simple_provider_name == comparable_name,
                col(WatchProvider.logo_url).is_not(None),
            )
            if logo_url := self.session.exec(statement).first():
                return logo_url
        return self.favicon_url()


class AmazonImporter(AmazonImporterUpsert, ABC):
    @override
    def parse_url(self, url: str) -> ParsedURL:
        detail_file = self.detail_file(self.link_id_from_url(url))
        self.raise_invalid_url_if_no_content(detail_file, url)
        return ParsedURL(detail_file.parsed().title_key)

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        title_key = media_info.title_key
        results: list[URLImportResult] = []
        # Need to get all titles because each individual source needs to be added to the
        # channel if no match is found on TMDB.
        if titles := list(self._preload_title(title_key, preload_episodes=True).all()):
            for title in titles:
                results += self._import_results(title, media_info)
            return results

        self._preload_and_download_files(media_info.title_key)
        for source in self.title_sources(media_info.title_key):
            title = self._upsert_title(source, media_info.title_key)
            results += self._import_results(title, media_info)
        return results

    @override
    def _update_and_upsert_title(self, title: Title) -> None:
        # Updating an Amazon title is a little complex because when a single title is
        # updated it needs to be updated for all sources.
        existing_titles = self._preload_title(title.key, preload_episodes=True).all()
        # All titles share files so only the files for the first title need to be
        # preloaded and downloaded because it will cover all titles.
        self._preload_and_download_files(existing_titles[0])

        sources = self.title_sources(title.key)
        source_ids = {source.id for source in sources}

        # Delete titles that are no longer available on a specific source.
        for preloaded_title in existing_titles:
            if preloaded_title.source_id not in source_ids:
                preloaded_title.soft_delete()

        # Upsert titles for all available sources which will detect new sources for
        # existing titles.
        for source in sources:
            self._upsert_title(source, title.key)
