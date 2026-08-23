# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from typing import Any, override

from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.NHKWorld import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON


# TODO: Validate
class NHKWorldEndpointJSON[T](EndpointJSON[T]):
    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


# TODO: Validate
class NHKWorldJSON(NHKWorldEndpointJSON[dict[str, Any]]):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)


# TODO: Validate
class NHKWorldListJSON(NHKWorldEndpointJSON[list[dict[str, Any]]]):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return self.raise_if_not_is_instance(raw, list)


# TODO: Validate
def published_at(item: dict[str, Any]) -> datetime:
    return tz_datetime.fromisoformat(item["video"]["published_at"])


# TODO: Validate
def expired_at(item: dict[str, Any]) -> datetime:
    return tz_datetime.fromisoformat(item["video"]["expired_at"])


# TODO: Validate
def first_broadcasted_at(item: dict[str, Any]) -> datetime:
    return tz_datetime.fromisoformat(item["first_broadcasted_at"])


# TODO: Validate
class VideoProgram(NHKWorldJSON):
    """Video program file."""

    # Occurs when a user puts in an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.NHKWorldNotFoundError)

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.video_programs(self.unique_identifier)


# TODO: Validate
class VideoEpisodes(NHKWorldListJSON):
    """Video episodes file."""

    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        return api.video_episodes_all(self.unique_identifier)

    # TODO: Validate
    def items(self) -> list[dict[str, Any]]:
        return [item for page in self.parsed() for item in page["items"]]


# TODO: Validate
class ShowsSearch(NHKWorldJSON):
    """Shows search file."""

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
    def _fetch(self) -> dict[str, Any]:
        return api.shows_search(self.query, from_=self.offset)


# TODO: Validate
class NewVideoEpisodes(NHKWorldListJSON):
    """New video episodes file."""

    IMMUTABLE = True

    # TODO: Consider moving this login into naphki
    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        to_datetime = self.identifier_datetime()
        pages: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = api.video_episodes(offset=offset)
            pages.append(page)
            pagination = page["pagination"]
            offset += pagination["count"]
            reached_datetime = any(
                published_at(item) <= to_datetime for item in page["items"]
            )
            if (
                pagination["next"] is None
                or pagination["count"] == 0
                or reached_datetime
            ):
                break
        return pages

    # TODO: Validate
    def items(self) -> list[dict[str, Any]]:
        return [item for page in self.parsed() for item in page["items"]]


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
            item["id"]
            for season_key in season_keys
            for item in self.video_episodes_file(season_key).items()
        ]

    # TODO: Validate
    def _get_image_url(self, images: Sequence[dict[str, Any]]) -> str:
        largest = max(images, key=lambda image: image["width"])
        return self.build_url(largest["url"])
