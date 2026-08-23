# TODO: Validate
"""The files a Netflix title is read out of.

Netflix answers with the whole of a title at once, so a show, its seasons and
their episodes all come out of the one file the title is downloaded as.
"""

from collections.abc import Sequence
from typing import Any, override

from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.Netflix import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON


# TODO: Validate
class NetflixJSON(EndpointJSON[dict[str, Any]]):
    """A file holding one Netflix GraphQL response."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)

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
class Title(NetflixJSON):
    """Title file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.lodp_title_and_plans_page(self.unique_identifier)


# TODO: Validate
class Search(NetflixJSON):
    """Search file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        cursor: str,
    ) -> None:
        """Initialize the file."""
        self.query = query
        self.cursor = cursor
        super().__init__(session, plugin, f"{query}/{cursor}")

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.search_page_results(self.query, self.cursor or None)


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a Netflix title is read out of."""

    # TODO: Validate
    def title_file(self, title_key: str) -> Title:
        """Contains all of a Netflix title's data (show, seasons, episodes)."""
        return self._file(Title, title_key)

    # TODO: Validate
    def search_file(self, query: str, cursor: str | None) -> Search:
        """Contains one page of Netflix's movie and TV search results."""
        return self._file(Search, query, cursor or "")

    # TODO: Validate
    def _title_video(self, show_key: str) -> dict[str, Any]:
        parsed = self.title_file(show_key).parsed()
        video = next(
            (
                video
                for video in parsed["data"]["videos"]
                if video["videoId"] == int(show_key)
            ),
            None,
        )
        if video is None:
            msg = f"No title found for {show_key}"
            raise ValueError(msg)
        return video

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self._title_video(show_key)["__typename"] == "Movie"

    # TODO: Validate
    def _ordered_seasons(self, show_key: str) -> list[dict[str, Any]]:
        seasons = self._title_video(show_key).get("seasons")
        if seasons is None:
            return []
        return [edge["node"] for edge in seasons["edges"]]

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_id: int,
    ) -> list[dict[str, Any]]:
        for season in self._ordered_seasons(show_key):
            if season["videoId"] == season_id:
                return [edge["node"] for edge in season["episodes"]["edges"]]
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
            self._season_key(show_key, season["videoId"])
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
                    str(episode["videoId"])
                    for episode in self._season_episodes(show_key, int(season_id))
                ]
        return episode_keys
