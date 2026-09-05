# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.files.models import File
from plugins.NHKWorld.files import (
    NewVideoEpisodes,
    ShowsSearch,
    VideoEpisodes,
    VideoProgram,
)
from plugins.utils.base_plugin_v3.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def shows_search_file(self, query: str, offset: int) -> ShowsSearch:
        """Contains one page of results for a search query."""
        return self._file(ShowsSearch, query, offset)

    # TODO: Validate
    def video_program_file(self, show_key: str) -> VideoProgram:
        """Contains a single show's information."""
        return self._file(VideoProgram, show_key)

    # TODO: Validate
    def video_episodes_file(self, program_id: str) -> VideoEpisodes:
        """Contains a show's episodes."""
        return self._file(VideoEpisodes, program_id)

    # TODO: Consider making this a generic function
    # TODO: Validate
    def new_video_episodes_file(
        self,
        feed_datetime: datetime | File,
    ) -> NewVideoEpisodes:
        """Contains the newest videos on the website."""
        if isinstance(feed_datetime, File):
            str_datetime = NewVideoEpisodes.file_to_unique_identifier(feed_datetime)
        else:
            str_datetime = str(feed_datetime)
        return self._file(NewVideoEpisodes, str_datetime)

    # TODO: Validate
    def latest_new_video_episodes_file(self) -> NewVideoEpisodes | None:
        """Return the latest new video episodes file, or None if none exists."""
        if file := self.preload_latest_file(NewVideoEpisodes):
            return self.new_video_episodes_file(file)
        return None

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[NewVideoEpisodes]:
        if file := self.latest_new_video_episodes_file():
            return [file]
        return []
