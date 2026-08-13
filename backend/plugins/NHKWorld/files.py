# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, override

from naphki import Naphki
from naphki.shows_search.models import ShowsSearchModel
from naphki.video_episodes import models as video_episodes_models
from naphki.video_episodes.models import Item, VideoEpisodesModel
from naphki.video_programs import models as video_programs_models
from naphki.video_programs.models import VideoProgramsModel
from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, GAPIListJSON
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def naphki() -> Naphki:
    return Naphki(get_around_client=get_around_client())


# TODO: Validate
class VideoProgram(GAPIJSON[VideoProgramsModel]):
    """Video program file."""

    # Occurs when a user puts in an invalid URL.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = naphki().video_programs


# TODO: Validate
class VideoEpisodes(GAPIListJSON[VideoEpisodesModel]):
    """Video episodes file."""

    API_ENDPOINT = naphki().video_episodes

    # TODO: Validate
    @override
    def _get(self) -> list[VideoEpisodesModel]:
        return naphki().video_episodes.download_and_parse_all(self.unique_identifier)

    # TODO: Validate
    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


# TODO: Validate
class ShowsSearch(GAPIJSON[ShowsSearchModel]):
    """Shows search file."""

    API_ENDPOINT = naphki().shows_search

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        offset: int,
    ) -> None:
        self.query = query
        self.offset = offset
        super().__init__(session, plugin, f"{query}/{offset}")

    # `size` keeps its default so a page request looks exactly like the one the
    # website makes.
    # TODO: Validate
    @override
    def _get(self) -> ShowsSearchModel:
        endpoint = naphki().shows_search
        return endpoint.parse(endpoint.download(self.query, from_=self.offset))


# TODO: Validate
class NewVideoEpisodes(GAPIListJSON[VideoEpisodesModel]):
    """New video episodes file."""

    IMMUTABLE = True
    API_ENDPOINT = naphki().video_episodes

    # TODO: Consider moving this login into naphki
    # TODO: Validate
    @override
    def _get(self) -> list[VideoEpisodesModel]:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        to_datetime = self.identifier_datetime()
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

    # TODO: Validate
    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    # The new episodes feed belongs to the source, so every show reads the same one.
    _PLUGIN_WIDE_FILES = (NewVideoEpisodes,)

    # TODO: Validate
    def video_program_file(self, show_key: str) -> VideoProgram:
        """Contains a single show's information."""
        return self._file(VideoProgram, show_key)

    # TODO: Validate
    def video_episodes_file(self, program_id: str) -> VideoEpisodes:
        """Contains a show's episodes."""
        return self._file(VideoEpisodes, program_id)

    # TODO: Validate
    def shows_search_file(self, query: str, offset: int) -> ShowsSearch:
        """Contains one page of results for a search query."""
        return self._file(ShowsSearch, query, offset)

    # TODO: Consider making this a generic function
    # TODO: Validate
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

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show.
        return [self.video_program_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season.
            self.video_program_file(show_key),
            # Required to detect new episodes.
            self.video_episodes_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.video_episodes_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        # There are no seasons on NHK World, but the value returned should still match
        # the value used for Season.key.
        return [show_key]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            item.id
            for season_key in season_keys
            for item in self.video_episodes_file(season_key).items()
        ]

    # TODO: Validate
    def _get_image_url(
        self,
        images: Sequence[
            video_programs_models.PortraitItem
            | video_programs_models.LandscapeItem
            | video_episodes_models.Image
        ],
    ) -> str:
        largest = max(images, key=lambda image: image.width)
        return self.build_url(largest.url)
