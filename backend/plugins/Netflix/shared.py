# TODO: Validate
"""What the plugin, its importers and its initializer all read Netflix by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, override

from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.files import (
    DetailModal,
    LodpTitleAndPlansPage,
    PreviewModalEpisodeSelector,
    PreviewModalEpisodeSelectorSeasonEpisodes,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from meshfilm.detail_modal.models import DetailModalModel

    from app.titles.models import Title


# TODO: Validate
class NetflixShared(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Netflix"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Netflix", "Netflix Standard with Ads")

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
    @classmethod
    def episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    def similar_file(self, title_key: str) -> LodpTitleAndPlansPage:
        return self._cached_file(LodpTitleAndPlansPage, title_key)

    # TODO: Validate
    def title_file(self, title_key: str) -> DetailModal:
        return self._cached_file(DetailModal, title_key)

    def seasons_file(self, title_key: str) -> PreviewModalEpisodeSelector:
        return self._cached_file(PreviewModalEpisodeSelector, title_key)

    def season_episodes_file(
        self,
        season_video_key: str | int,
    ) -> PreviewModalEpisodeSelectorSeasonEpisodes:
        return self._cached_file(
            PreviewModalEpisodeSelectorSeasonEpisodes,
            str(season_video_key),
        )


# TODO: Validate
class NetflixImporterChannels(NetflixShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        title_data = self.title_file(title.key).parsed()
        channel_keys = ["All Titles", *self._title_channel_keys(title_data)]
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])
        for channel_key, urls in self._related_urls(title_data).items():
            self.add_new_urls_to_channel(channel_key, urls)

    # TODO: Validate
    def _genre_names(self, title_data: DetailModalModel) -> list[str]:
        genre_tags = title_data.genre_tags.edges if title_data.genre_tags else None
        return [
            edge.node.name for edge in genre_tags or [] if edge.node and edge.node.name
        ]

    # TODO: Validate
    def _title_channel_keys(self, title_data: DetailModalModel) -> list[str]:
        channel_keys = [
            mood_tag.display_name
            for mood_tag in title_data.mood_tags
            if mood_tag.display_name
        ]
        channel_keys.extend(self._genre_names(title_data))
        channel_keys.extend(
            membership.title
            for membership in title_data.title_group_memberships
            if membership.title
        )
        return list(dict.fromkeys(channel_keys))

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
