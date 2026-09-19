# TODO: Validate
"""What the plugin, its importers and its initializer all read NHK World by."""

from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from app.files.models import File
from app.utils import tz_datetime
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.files import (
    NewVideoEpisodes,
    VideoEpisodes,
    VideoProgram,
    VideoPrograms,
)
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from naphki.video_episodes.models import Image as EpisodeImage
    from naphki.video_program.models import LandscapeItem, PortraitItem

    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile

MINIMUM_THUMBNAIL_WIDTH = 480


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://www3.nhk.or.jp/{path.lstrip('/')}"


# TODO: Validate
def image_url(images: Sequence[LandscapeItem | PortraitItem | EpisodeImage]) -> str:
    largest = max(images, key=lambda image: image.width)
    return build_url(largest.url)


# TODO: Validate
def thumbnail_url(images: Sequence[LandscapeItem | PortraitItem | EpisodeImage]) -> str:
    wide_enough = [image for image in images if image.width >= MINIMUM_THUMBNAIL_WIDTH]
    chosen = (
        min(wide_enough, key=lambda image: image.width)
        if wide_enough
        else max(images, key=lambda image: image.width)
    )
    return build_url(chosen.url)


# TODO: Validate
class NHKWorldShared(BasePlugin):
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
        return build_url(f"nhkworld/en/shows/{title_key}/")

    # TODO: Validate
    def video_programs_file(self) -> VideoPrograms:
        return self._cached_file(VideoPrograms)

    # TODO: Validate
    def video_program_file(self, title_key: str) -> VideoProgram:
        """Contains a single title's information."""
        return self._cached_file(VideoProgram, title_key)

    # TODO: Validate
    def video_episodes_file(self, program_id: str) -> VideoEpisodes:
        """Contains a title's episodes."""
        return self._cached_file(VideoEpisodes, program_id)

    # TODO: Consider making this a generic function
    # TODO: Validate
    def new_video_episodes_file(
        self,
        feed_datetime: datetime | File,
    ) -> NewVideoEpisodes:
        """Contains the newest videos on the website."""
        if isinstance(feed_datetime, File):
            return self._cached_file(
                NewVideoEpisodes,
                NewVideoEpisodes.file_to_unique_identifier(feed_datetime),
            )
        return self._cached_file(NewVideoEpisodes, str(feed_datetime))

    # TODO: Validate
    def latest_new_video_episodes_file(self) -> NewVideoEpisodes | None:
        """Return the latest new video episodes file, or None if none exists."""
        if file := self.latest_file_record(NewVideoEpisodes):
            return self.new_video_episodes_file(file)
        return None

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[NewVideoEpisodes]:
        if file := self.latest_new_video_episodes_file():
            return [file]
        return [self.new_video_episodes_file(tz_datetime.now())]

    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Detects changes to the title.
        return [self.video_program_file(title_key)]

    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Detects changes to the season.
            self.video_program_file(title_key),
            # Detects new episodes.
            self.video_episodes_file(title_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Detects changes to the episode.
        return [self.video_episodes_file(title_key)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        # NHK World has no seasons,
        return [title_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            item.id
            for season_key in season_keys
            for item in self.video_episodes_file(season_key).items()
        ]

    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        program = self.video_program_file(title.key).parsed()
        channel_keys = ["All Titles"]
        channel_keys.extend(category.name for category in program.categories)
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])

    @override
    def create_initial_channel_records(self) -> None:
        self.video_programs_file().download_if_outdated()
        title_keys = [item.id for item in self.video_programs_file().items()]
        self._add_titles_to_all_titles_channel(title_keys)

    def _create_channel_records_from_incomplete_feed_files(self) -> None:
        for feed_file in self._incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        ):
            title_keys = [item.video_program.id for item in feed_file.items()]
            self._add_titles_to_all_titles_channel(title_keys)
            feed_file.clear_status()


# TODO: Validate


# TODO: Validate
class NHKWorldImporter(NHKWorldShared, BaseImporter, ABC):
    pass
