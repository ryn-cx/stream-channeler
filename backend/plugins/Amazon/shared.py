"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

import re
from abc import ABC
from contextlib import suppress
from functools import cached_property
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import func
from sqlmodel import col, select

from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.users.service.accounts import get_or_create_automatic_channel_user
from app.watch_providers.models import WatchProvider
from plugins.Amazon.constants import (
    AMAZON_PRODUCT_URL_REGEX,
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
)
from plugins.Amazon.files import Detail
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from app.users.models import User
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class AmazonShared(BasePluginCore):
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
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    @classmethod
    @override
    def _domains(cls) -> list[str]:
        return ["primevideo.com", "amazon.com"]

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX, AMAZON_PRODUCT_URL_REGEX)

    # TODO: Validate
    def link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in self._url_regexes():
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

    # TODO: Validate
    @override
    def _title_keys_by_url(self, urls: Collection[str]) -> dict[str, str]:
        link_ids_by_url: dict[str, str] = {}
        for url in urls:
            with suppress(InvalidURLError):
                link_ids_by_url[url] = self.link_id_from_url(url)
        link_ids = set(link_ids_by_url.values())
        title_keys_by_link_id = {
            title_key: title_key
            for title_key in self.session.exec(
                select(Title.key)
                .join(Source, col(Title.source_id) == col(Source.id))
                .where(
                    Source.plugin_id == self.plugin.id,
                    col(Title.key).in_(link_ids),
                ),
            ).all()
        }
        title_keys_by_link_id |= dict(
            self.session.exec(
                select(Season.key, Title.key)
                .join(Title, col(Season.title_id) == col(Title.id))
                .join(Source, col(Title.source_id) == col(Source.id))
                .where(
                    Source.plugin_id == self.plugin.id,
                    col(Season.key).in_(link_ids - title_keys_by_link_id.keys()),
                ),
            ).all(),
        )
        return {
            url: title_keys_by_link_id[link_id]
            for url, link_id in link_ids_by_url.items()
            if link_id in title_keys_by_link_id
        }

    def detail_file(self, link_id: str) -> Detail:
        return self._cached_file(Detail, link_id)


# TODO: Validate
class AmazonImporterChannels(AmazonShared, BaseUpserter, ABC):
    # TODO: Validate
    @override
    def _canonical_title_key(self, title_key: str) -> str:
        detail_file = self.detail_file(title_key)
        if not detail_file.record_content:
            return title_key
        return detail_file.parsed().title_key

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

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        parsed = self.detail_file(title.key).parsed()
        # TODO: Do I care about Amazon purchases>
        channel_keys: list[str] = []
        if parsed.purchasable:
            channel_keys.append("Purchase")
        channel_keys.extend(parsed.genres)
        channel_keys.extend(parsed.studios)
        channel_keys.extend(
            f"{audio_track} Audio" for audio_track in parsed.audio_tracks
        )
        channel_keys.extend(f"{subtitle} Subtitles" for subtitle in parsed.subtitles)

        self.add_title_to_channel("All Titles", title)
        self.set_title_tag_channels(title, channel_keys)

    # TODO: Validate
    def add_other_titles_on_page_to_channels(self, title: Title) -> None:
        title_urls = self.detail_file(title.key).subscription_title_urls_on_this_page()
        self.add_new_urls_to_channel("All Titles", title_urls)

    # TODO: Validate
    @override
    def add_title_to_channels(self, title: Title) -> None:
        super().add_title_to_channels(title)
        self.add_other_titles_on_page_to_channels(title)

    # TODO: Validate
    @override
    def _preload_and_download_files(self, title: Title | str) -> None:
        super()._preload_and_download_files(title)
        self.download_other_titles_on_page(
            title if isinstance(title, str) else title.key,
        )

    # TODO: Validate
    def download_other_titles_on_page(self, title_key: str) -> None:
        title_urls = self.detail_file(title_key).subscription_title_urls_on_this_page()
        detail_files: list[Detail] = []
        for url in title_urls:
            with suppress(InvalidURLError):
                detail_files.append(self.detail_file(self.link_id_from_url(url)))
        self._preload_files(detail_files, load_content=False)
        for detail_file in detail_files:
            if detail_file.does_not_exist():
                detail_file.download_if_outdated()


# TODO: Validate
class AmazonImporter(AmazonImporterChannels, ABC):
    @override
    def parse_url(self, url: str) -> ParsedURL:
        detail_file = self.detail_file(self.link_id_from_url(url))
        self.raise_invalid_url_if_no_content(detail_file, url)
        return ParsedURL(detail_file.parsed().title_key)

    # TODO: Validate
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
        parsed = self.detail_file(title_key).parsed()
        if superseded_titles := self._superseded_titles(
            title_key,
            parsed.parent_title or parsed.title,
        ):
            self._rekey_superseded_titles(superseded_titles, title_key)

        upserted_titles = [
            self._upsert_title(source, media_info.title_key)
            for source in self.title_sources(media_info.title_key)
        ]
        for upserted_title in upserted_titles:
            self.add_title_to_channels(upserted_title)
            results += self._import_results(upserted_title, media_info)
        for superseded_title in superseded_titles:
            if superseded_title.deleted_at is not None:
                self.remove_title_from_plugin_channels(superseded_title)
        return results

    # TODO: Validate
    @override
    def _update_and_upsert_title(self, title: Title) -> None:
        # Updating an Amazon title is a little complex because when a single title is
        # updated it needs to be updated for all sources.
        existing_titles = self._preload_title(title.key, preload_episodes=True).all()
        # All titles share files so only the files for the first title need to be
        # preloaded and downloaded because it will cover all titles.
        self._preload_and_download_files(existing_titles[0])

        title_key = title.key
        canonical_key = self._canonical_title_key(title_key)
        if canonical_key != title_key:
            existing_titles = [
                *existing_titles,
                *self._rekey_superseded_titles(existing_titles, canonical_key),
            ]
            title_key = canonical_key
            self._preload_and_download_files(title_key)

        sources = self.title_sources(title_key)
        source_ids = {source.id for source in sources}

        # Delete titles that are no longer available on a specific source.
        for preloaded_title in existing_titles:
            if preloaded_title.source_id not in source_ids:
                preloaded_title.soft_delete()

        # Upsert titles for all available sources which will detect new sources for
        # existing titles.
        upserted_titles = [self._upsert_title(source, title_key) for source in sources]
        for upserted_title in upserted_titles:
            self.add_title_to_channels(upserted_title)
        for existing_title in existing_titles:
            if existing_title.deleted_at is not None:
                self.remove_title_from_plugin_channels(existing_title)

    # TODO: Validate
    def _get_or_create_source(self, source_key: str) -> Source:
        """Get or create a source if it doesn't already exist."""
        if source_key not in self._sources:
            self._sources[source_key] = self.upsert_source(
                source_key,
                favicon_url=self._source_favicon_url(source_key),
            )
        return self._sources[source_key]

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
        return sources or [self._sources["Unavailable on Amazon"]]

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
