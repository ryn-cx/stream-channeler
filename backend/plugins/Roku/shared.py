# TODO: Validate
"""What the plugin, its importers and its initializer all read Roku by."""

from __future__ import annotations

import re
from abc import ABC
from datetime import UTC
from typing import TYPE_CHECKING, Any, override

from plugins.Roku.constants import (
    DETAILS_URL_REGEX,
    MOVIE_TYPE,
    WATCH_URL_REGEX,
)
from plugins.Roku.files import ContentFile
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nana.content.models import ContentModel

    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class RokuShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"details/{title_key}")

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://therokuchannel.roku.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (DETAILS_URL_REGEX, WATCH_URL_REGEX)

    # TODO: Validate
    def content_file(self, content_key: str) -> ContentFile:
        return self._cached_file(ContentFile, content_key)

    # TODO: Validate
    def _url_content_key(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                return match.group(1)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @staticmethod
    def is_movie(content: ContentModel) -> bool:
        content_type = content.type
        if content_type not in (MOVIE_TYPE, "series"):
            msg = f"Invalid media type: {content_type}"
            raise RuntimeError(msg)
        return content_type == MOVIE_TYPE


# TODO: Validate
class RokuImporter(RokuShared, BaseUpserter, ABC):
    # TODO: Validate
    def _content(self, content_key: str) -> ContentModel:
        return self.content_file(content_key).parsed()

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]

    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_number: int) -> str:
        return f"{title_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, int]:
        title_key, _, season_number = season_key.rpartition(":")
        return title_key, int(season_number)

    # TODO: Validate
    def _set_expiry_update_at(self, title: Title) -> None:
        for view_option in self._content(title.key).view_options:
            validity_end_time = view_option.media.validity_end_time
            if validity_end_time:
                expires_at = validity_end_time.replace(
                    tzinfo=validity_end_time.tzinfo or UTC,
                )
                title.set_update_at(expires_at)
                for season in title.seasons:
                    season.set_update_at(expires_at)

    # TODO: Validate
    @override
    def _url_content_key(self, url: str) -> str:
        key = super()._url_content_key(url)
        self.raise_invalid_url_if_no_content(self.content_file(key), url)
        return key

    # TODO: Validate
    @classmethod
    def video_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")
