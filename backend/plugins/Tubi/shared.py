# TODO: Validate
"""What the plugin, its importers and its initializer all read Tubi by."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override

from plugins.Tubi.constants import (
    EPISODE_URL_REGEX,
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
)
from plugins.Tubi.files import ContentFile
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugi.content.models import ContentModel

    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def is_movie(content: ContentModel) -> bool:
    # The `type` field of a Tubi content response marks a series; a movie
    # and a single episode both use "v".
    return content.type != "s"


# TODO: Validate
class TubiShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Tubi"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX, EPISODE_URL_REGEX)


# TODO: Validate
class TubiImporter(TubiShared, BaseUpserter, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the title's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:
            msg = "Title.url is not set."
            raise AttributeError(msg)

        self.add_title_to_channel("All Titles", title)
        self.set_title_tag_channels(title, self._content(title.key).tags)

    # TODO: Validate
    @staticmethod
    def first_image(images: list[str]) -> str | None:
        return images[0] if images else None

    # TODO: Validate
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._cached_file(ContentFile, content_id)

    # TODO: Validate
    def _content(self, title_key: str) -> ContentModel:
        return self.content_file(title_key).parsed()

    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_id: str) -> str:
        """Encode the title key into the season key.

        Every entity's data comes from the single content file keyed by the title,
        but the base plugin resolves episode files from a season key alone, so the
        title key is included inside it.
        """
        return f"{title_key}:{season_id}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, str]:
        title_key, _, season_id = season_key.partition(":")
        return title_key, season_id
