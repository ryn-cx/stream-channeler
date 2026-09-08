# TODO: Validate
from __future__ import annotations

from datetime import datetime
from functools import singledispatchmethod
from typing import TYPE_CHECKING, override

from app.files.models import File
from plugins.NHKWorld.files import (
    NewVideoEpisodes,
    TitlesSearch,
    VideoEpisodes,
    VideoProgram,
)
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class NHKWorldBaseFiles(BasePlugin):
    # TODO: Validate
    def titles_search_file(self, query: str, offset: int) -> TitlesSearch:
        """Contains one page of results for a search query."""
        return self._cached_file(TitlesSearch, query, offset)

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
    @singledispatchmethod
    def new_video_episodes_file(
        self,
        feed_datetime: datetime | File,  # noqa: ARG002
    ) -> NewVideoEpisodes:
        """Contains the newest videos on the website."""
        raise TypeError

    # TODO: Validate
    @new_video_episodes_file.register
    def _new_video_episodes_file_by_datetime(
        self,
        feed_datetime: datetime,
    ) -> NewVideoEpisodes:
        return self._cached_file(NewVideoEpisodes, str(feed_datetime))

    # TODO: Validate
    @new_video_episodes_file.register
    def _new_video_episodes_file_by_record(
        self,
        feed_datetime: File,
    ) -> NewVideoEpisodes:
        return self._cached_file(
            NewVideoEpisodes,
            NewVideoEpisodes.file_to_unique_identifier(feed_datetime),
        )

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
        return []
