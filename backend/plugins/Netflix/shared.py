# TODO: Validate
"""What the plugin, its importers and its initializer all read Netflix by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, override

from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.files import DetailModal
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from meshfilm.detail_modal.models import DetailModalModel

    from app.titles.models import Title


# TODO: Validate
class NetflixShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Netflix"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.netflix.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @classmethod
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"title/{title_key}")

    # TODO: Validate
    def title_file(self, title_key: str) -> DetailModal:
        return self._cached_file(DetailModal, title_key)


# TODO: Validate
class NetflixImporterChannels(NetflixShared, BaseUpserter, ABC):
    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        title_file = self.title_file(title.key)
        title_data = title_file.parsed()
        self.set_title_tag_channels(title, self._tag_channel_keys(title_data))
        related_urls = self._related_urls(title_data)
        self.add_title_to_channel("All Titles", title)
        self.add_new_urls_to_channel("All Titles", related_urls["All Titles"])
        self.replace_list_channels(
            {
                channel_key: [title.url, *related_urls.get(channel_key, [])]
                for channel_key in self._list_channel_keys(title_data)
            },
            title_file.record_data_timestamp,
        )

    # TODO: Validate
    def _genre_names(self, title_data: DetailModalModel) -> list[str]:
        genre_tags = title_data.genre_tags.edges if title_data.genre_tags else None
        return [
            edge.node.name for edge in genre_tags or [] if edge.node and edge.node.name
        ]

    # TODO: Validate
    def _tag_channel_keys(self, title_data: DetailModalModel) -> list[str]:
        channel_keys = [
            mood_tag.display_name
            for mood_tag in title_data.mood_tags
            if mood_tag.display_name
        ]
        channel_keys.extend(self._genre_names(title_data))
        return list(dict.fromkeys(channel_keys))

    # TODO: Validate
    def _list_channel_keys(self, title_data: DetailModalModel) -> list[str]:
        return list(
            dict.fromkeys(
                membership.title
                for membership in title_data.title_group_memberships
                if membership.title
            ),
        )

    # TODO: Validate
    def _related_urls(
        self,
        title_data: DetailModalModel,
    ) -> dict[str, list[str]]:
        urls_by_channel_key: dict[str, dict[str, None]] = {
            "All Titles": {
                self.title_url(str(similar.video_id)): None
                for similar in title_data.similars
                if similar.video_id
            },
        }
        for membership in title_data.title_group_memberships:
            for sibling in membership.siblings or []:
                video_id = sibling.video_id
                if not video_id:
                    continue
                url = self.title_url(str(video_id))
                urls_by_channel_key["All Titles"][url] = None
                if membership.title:
                    urls_by_channel_key.setdefault(membership.title, {})[url] = None
        return {
            channel_key: list(urls) for channel_key, urls in urls_by_channel_key.items()
        }


# TODO: Validate


# TODO: Validate
class NetflixImporter(NetflixImporterChannels, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.title_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @classmethod
    def episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")
