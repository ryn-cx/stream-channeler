# TODO: Validate
"""The files a Netflix title is read out of.

Netflix answers with the whole of a title at once, so a show, its seasons and
their episodes all come out of the one file the title is downloaded as.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from typing import Any, override

from meshfilm import Meshfilm
from meshfilm.lodp_title_and_plans_page import LodpTitleAndPlansPage
from meshfilm.lodp_title_and_plans_page.models import (
    LodpTitleAndPlansPageModel,
)
from meshfilm.lodp_title_and_plans_page.models import Node as SeasonNode
from meshfilm.lodp_title_and_plans_page.models import Node1 as EpisodeNode
from meshfilm.lodp_title_and_plans_page.models import Video1 as TitleVideo
from meshfilm.search_page_results import SearchPageResults
from meshfilm.search_page_results.models import SearchPageResultsModel
from sqlmodel import Session

from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    BaseFile,
    EndpointFile,
    IntegerEndpointFile,
)
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def meshfilm() -> Meshfilm:
    """Return a cached Meshfilm client."""
    return Meshfilm(get_around_client=get_around_client())


# TODO: Validate
class Title(IntegerEndpointFile[LodpTitleAndPlansPageModel]):
    """Title file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> LodpTitleAndPlansPage:
        return meshfilm().lodp_title_and_plans_page


# TODO: Validate
class Search(EndpointFile[SearchPageResultsModel]):
    """Search file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchPageResults:
        return meshfilm().search_page_results

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        cursor: str,
    ) -> None:
        self.query = query
        self.cursor = cursor
        super().__init__(session, plugin, f"{query}/{cursor}")

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, self.cursor or None)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a Netflix title is read out of."""

    # TODO: Validate
    def search_file(self, query: str, cursor: str | None) -> Search:
        """Contains one page of Netflix's movie and TV search results."""
        return self._file(Search, query, cursor or "")

    # TODO: Validate
    def title_file(self, title_key: str) -> Title:
        """Contains all of a Netflix title's data (show, seasons, episodes)."""
        return self._file(Title, title_key)

    # TODO: Validate
    def _title_video(self, show_key: str) -> TitleVideo:
        parsed = self.title_file(show_key).parsed()
        video = next(
            (video for video in parsed.data.videos if video.video_id == int(show_key)),
            None,
        )
        if video is None:
            msg = f"No title found for {show_key}"
            raise ValueError(msg)
        return video

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self._title_video(show_key).field__typename == "Movie"

    # TODO: Validate
    def _ordered_seasons(self, show_key: str) -> list[SeasonNode]:
        seasons = self._title_video(show_key).seasons
        if seasons is None:
            return []
        return [edge.node for edge in seasons.edges]

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_id: int,
    ) -> list[EpisodeNode]:
        for season in self._ordered_seasons(show_key):
            if season.video_id == season_id:
                return [edge.node for edge in season.episodes.edges]
        return []

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_id: str | int) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single title file keyed by the show,
        but the base plugin resolves episode files from a season key alone, so
        the show key is carried inside it.
        """
        return f"{show_key}:{season_id}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.title_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # A season is read out of the show's own file, so that is what says
        # whether the season has changed or gained an episode.
        return [self.title_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, show_key)]
        return [
            self._season_key(show_key, season.video_id)
            for season in self._ordered_seasons(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
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
                    str(episode.video_id)
                    for episode in self._season_episodes(show_key, int(season_id))
                ]
        return episode_keys
