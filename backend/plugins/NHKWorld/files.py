# TODO: Validate
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from typing import Any, ClassVar, override

from naphki import Naphki
from naphki.exceptions import ProgramNotFoundError
from naphki.video_episodes import VideoEpisodes as VideoEpisodesEndpoint
from naphki.video_episodes.models import Image as EpisodeImage
from naphki.video_episodes.models import Item, VideoEpisodesModel
from naphki.video_program import VideoProgram as VideoProgramEndpoint
from naphki.video_program.models import LandscapeItem, PortraitItem, VideoProgramModel

from app.files.models import File
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import PluginShowIdentity
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def naphki() -> Naphki:
    return Naphki(get_around_client=get_around_client())


# TODO: Validate
class VideoProgram(EndpointFile[VideoProgramModel]):
    """Video program file."""

    API_ENDPOINT: ClassVar[VideoProgramEndpoint] = naphki().video_program

    # Occurs when a user puts in an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ProgramNotFoundError)


# TODO: Validate
class VideoEpisodes(EndpointFile[VideoEpisodesModel]):
    """Video episodes file."""

    API_ENDPOINT: ClassVar[VideoEpisodesEndpoint] = naphki().video_episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download_merged_until_datetime(self.unique_identifier)

    # TODO: Validate
    def items(self) -> list[Item]:
        return self.parsed().items


# TODO: Validate
class NewVideoEpisodes(EndpointFile[VideoEpisodesModel]):
    """New video episodes file."""

    IMMUTABLE = True

    API_ENDPOINT: ClassVar[VideoEpisodesEndpoint] = naphki().video_episodes

    # TODO: Consider moving this login into naphki
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        return self.API_ENDPOINT.download_merged_until_datetime(
            end_datetime=self.identifier_datetime(),
        )

    # TODO: Validate
    def items(self) -> list[Item]:
        return self.parsed().items


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    # The new episodes feed belongs to the source, so every show reads the same one.
    # TODO: Validate
    @classmethod
    @override
    def _plugin_wide_files(cls) -> tuple[type[BaseFile[Any]], ...]:
        return (NewVideoEpisodes,)

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
        images: Sequence[LandscapeItem | PortraitItem | EpisodeImage],
    ) -> str:
        largest = max(images, key=lambda image: image.width)
        return self.build_url(largest.url)

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        program_file = self.video_program_file(show_key)
        program_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return PluginShowIdentity(
            title=program_file.parsed().title,
            media_type="TV Show",
        )
