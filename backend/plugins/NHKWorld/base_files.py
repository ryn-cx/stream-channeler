# TODO: Validate
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from app.files.models import File
from app.utils import tz_datetime
from plugins.NHKWorld.files import (
    NewVideoEpisodes,
    VideoEpisodes,
    VideoProgram,
    VideoPrograms,
)
from plugins.NHKWorld.utils import build_url
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NHKWorldBaseFiles(BasePlugin):
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
