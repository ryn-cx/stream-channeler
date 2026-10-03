# TODO: Validate
"""What the plugin, its importers and its initializer all read NHK World by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.files import VideoProgram
from plugins.utils.base_plugin.core import BasePluginCore

if TYPE_CHECKING:
    from app.titles.models import Title

MINIMUM_THUMBNAIL_WIDTH = 480


# TODO: Validate
class NHKWorldShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"

    # TODO: Add support for single episodes
    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"nhkworld/en/shows/{title_key}/")

    # TODO: Validate
    def video_program_file(self, title_key: str) -> VideoProgram:
        """Contains a single title's information."""
        return self._cached_file(VideoProgram, title_key)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        program = self.video_program_file(title.key).parsed()
        self.add_title_to_channel("All Titles", title)
        self.set_title_tag_channels(
            title,
            [category.name for category in program.categories],
        )


# TODO: Validate
