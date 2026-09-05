# TODO: Validate
"""The files a Tubi title is read out of."""

from collections.abc import Sequence
from datetime import timedelta
from functools import cache
from typing import Any, override

from plugi import Plugi
from plugi.content import Content as ContentEndpoint
from plugi.content.models import Child as SeasonChild
from plugi.content.models import Child1 as EpisodeChild
from plugi.content.models import ContentModel
from plugi.exceptions import ContentNotFoundError

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def plugi() -> Plugi:
    """Return a cached Plugi client."""
    return Plugi(get_around_client=get_around_client())


# TODO: Validate
class _ContentFile(EndpointFile[ContentModel]):
    """Content file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> ContentEndpoint:
        return plugi().content

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid content_id {self.unique_identifier}"

    # TODO: Validate
    def is_movie(self) -> bool:
        # The `type` field of a Tubi content response marks a series; a movie
        # and a single episode both use "v".
        return self.parsed().type != "s"

    # TODO: Validate
    def tmdb_lookup_info(self) -> list[TMDBLookupInfo]:
        self.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        content = self.parsed()
        return [
            TMDBLookupInfo(
                content.title,
                TMDBMediaType.movie if self.is_movie() else TMDBMediaType.tv,
                content.year,
            ),
        ]


# TODO: Validate
class FileMixin(BasePlugin):
    """The files a title is read out of."""

    # TODO: Validate
    def content_file(self, content_id: str) -> _ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._file(_ContentFile, content_id)

    # TODO: Validate
    def _content(self, content_id: str) -> ContentModel:
        return self.content_file(content_id).parsed()

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self.content_file(show_key).is_movie()

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[SeasonChild]:
        children = self._content(show_key).children
        if children is None:
            return []
        # Tubi returns the seasons in an arbitrary order.
        return sorted(children, key=lambda season: int(season.id))

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_id: str) -> list[EpisodeChild]:
        for season in self._seasons(show_key):
            if season.id == season_id:
                return season.children
        return []

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_id: str) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single content file keyed by the show,
        but the base plugin resolves episode files from a season key alone, so the
        show key is carried inside it.
        """
        return f"{show_key}:{season_id}"

    # TODO: Validate
    @classmethod
    def _movie_season_key(cls, show_key: str) -> str:
        # A movie has no seasons of its own so its single season is given a
        # fixed id.
        return cls._season_key(show_key, "0")

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the show's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._movie_season_key(show_key)]
        return [
            self._season_key(show_key, season.id) for season in self._seasons(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_id = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode.id for episode in self._season_episodes(show_key, season_id)
                ]
        return episode_keys
