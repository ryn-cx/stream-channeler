from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import override

from naphki import Naphki
from naphki.shows_search.models import ShowsSearchModel
from naphki.video_episodes.models import Item, VideoEpisodesModel
from naphki.video_programs.models import VideoProgramsModel
from sqlmodel import col, select

from app.files.models import File
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON
from plugins.utils.get_around_client import get_around_client


@cache
def naphki() -> Naphki:
    return Naphki(get_around_client=get_around_client())


class VideoProgram(GAPIJSON[VideoProgramsModel]):
    # Occurs when a user puts in an invalid URL.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = naphki().video_programs


class VideoEpisodes(GAPIListJSON[VideoEpisodesModel]):
    API_ENDPOINT = naphki().video_episodes

    @override
    def _get(self) -> list[VideoEpisodesModel]:
        return naphki().video_episodes.download_and_parse_all(self.unique_identifier)

    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


class ShowsSearch(GAPIJSON[ShowsSearchModel]):
    API_ENDPOINT = naphki().shows_search


class NewVideoEpisodes(GAPIListJSON[VideoEpisodesModel]):
    IMMUTABLE = True
    API_ENDPOINT = naphki().video_episodes

    # TODO: Consider moving this login into naphki
    @override
    def _get(self) -> list[VideoEpisodesModel]:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        to_datetime = tz_datetime.fromisoformat(self.unique_identifier)
        pages: list[VideoEpisodesModel] = []
        offset = 0
        while True:
            page = naphki().video_episodes.download_and_parse(offset=offset)
            pages.append(page)
            offset += page.pagination.count
            reached_datetime = any(
                item.video.published_at <= to_datetime for item in page.items
            )
            if (
                page.pagination.next is None
                or page.pagination.count == 0
                or reached_datetime
            ):
                break
        return pages

    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


class FileMixin(BasePlugin, register=False):
    def video_program_file(self, show_key: str) -> VideoProgram:
        """Contains a single show's information."""
        return self._get_cached_file(
            VideoProgram,
            show_key,
            lambda: VideoProgram(self.session, self.plugin, show_key),
        )

    def video_episodes_file(self, program_id: str) -> VideoEpisodes:
        """Contains a show's episodes."""
        return self._get_cached_file(
            VideoEpisodes,
            program_id,
            lambda: VideoEpisodes(self.session, self.plugin, program_id),
        )

    def shows_search_file(self, query: str) -> ShowsSearch:
        """Contains results for a search query."""
        return self._get_cached_file(
            ShowsSearch,
            query,
            lambda: ShowsSearch(self.session, self.plugin, query),
        )

    # TODO: Consider making this a generic function
    def new_video_episodes_file(
        self,
        feed_datetime: datetime | File,
    ) -> NewVideoEpisodes:
        """Contains the newest videos on the website."""
        if isinstance(feed_datetime, File):
            str_datetime = NewVideoEpisodes.file_key_to_unique_identifier(
                feed_datetime.key,
            )
        else:
            str_datetime = str(feed_datetime)
        return self._get_cached_file(
            NewVideoEpisodes,
            str_datetime,
            lambda: NewVideoEpisodes(self.session, self.plugin, str_datetime),
        )

    # TODO: Consider making this a generic function
    def latest_new_video_episodes_file(self) -> NewVideoEpisodes:
        """Return the latest new video episodes file, downloading one if none exist."""
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{NewVideoEpisodes.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        if file := self.session.exec(statement).first():
            return self.new_video_episodes_file(file)
        feed = self.new_video_episodes_file(tz_datetime.now())
        feed.download_if_outdated()
        return feed

    # TODO: Consider if a _source_files function should exist.
    @override
    def _show_files(self, show_key: str) -> Sequence[VideoProgram]:
        # Required to detect changes to the show.
        return [self.video_program_file(show_key)]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[VideoEpisodes | VideoProgram]:
        return [
            # Required to detect changes to the season.
            self.video_program_file(show_key),
            # Required to detect new episodes.
            self.video_episodes_file(show_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[VideoEpisodes]:
        # Required to detect changes to the episode.
        return [self.video_episodes_file(show_key)]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        # There are no seasons on NHK World, but the value returned should still match
        # the value used for Season.key.
        return [show_key]

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            item.id
            for season_key in season_keys
            for item in self.video_episodes_file(season_key).items()
        ]
