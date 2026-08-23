# TODO: Validate
"""The files Paramount+ is read out of."""

import re
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any, override

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.ParamountPlus import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    BaseFile,
    EndpointJSON,
    HTMLFile,
)
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client

_SEASON_LABEL_REGEX = re.compile(r"^Season \d+")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_PAGE_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.paramountplus.com/shows/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0, i",
}


# TODO: Validate
class ParamountPlusJSON(EndpointJSON[dict[str, Any]]):
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
class ShowPage(HTMLFile):
    """Show page file."""

    _SEASON_STRAINER = SoupStrainer(attrs={"data-value": True})

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, show_id: str) -> None:
        """Initialize the file."""
        self.show_id = show_id
        super().__init__(session, plugin, show_id)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.show_id):
            url = f"https://www.paramountplus.com/shows/{self.show_id}/"
            response = get_around_client().get(
                url,
                headers=_PAGE_HEADERS,
                follow_redirects=True,
            )
            if response.status_code == HTTPStatus.NOT_FOUND:
                self.write(None, f"Invalid show {self.show_id}")
                return
            response.raise_for_status()
            self.write(response.text)

    # TODO: Validate
    @override
    def parsed(self) -> BeautifulSoup:
        """Return only the page's ``data-value`` elements.

        Straining at parse time avoids building the full (large) page tree.
        """
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            self._cached_parsed = BeautifulSoup(
                content,
                "lxml",
                parse_only=self._SEASON_STRAINER,
            )
        return self._cached_parsed

    # TODO: Validate
    def season_numbers(self) -> list[int]:
        """Return the show's available season numbers, sorted ascending."""
        numbers: set[int] = set()
        for element in self.parsed().find_all(attrs={"data-value": True}):
            if not isinstance(element, Tag):
                continue
            label = element.get("aria-label")
            value = element.get("data-value")
            if (
                isinstance(label, str)
                and isinstance(value, str)
                and _SEASON_LABEL_REGEX.match(label)
                and value.isdigit()
            ):
                numbers.add(int(value))
        return sorted(numbers)


# TODO: Validate
class EpisodesFile(ParamountPlusJSON):
    """Episodes file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_id: str,
        season_number: int,
    ) -> None:
        """Initialize the file."""
        self.show_id = show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{show_id}/{season_number}")

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.episodes(self.show_id, season_number=self.season_number)


# TODO: Validate
class MovieFile(ParamountPlusJSON):
    """Movie file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.movie(self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.MovieNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid movie_id {self.unique_identifier}"


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def show_page_file(self, show_id: str) -> ShowPage:
        """Return ShowPage file."""
        return self._file(ShowPage, show_id)

    # TODO: Validate
    def episodes_file(self, show_id: str, season_number: int) -> EpisodesFile:
        """Return EpisodesFile file."""
        return self._file(EpisodesFile, show_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        """Return MovieFile file."""
        return self._file(MovieFile, movie_id)

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)
        return self._media_type_value == "movie"

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    # TODO: Validate
    def _season_numbers(self, show_id: str) -> list[int]:
        return self.show_page_file(show_id).season_numbers()

    # TODO: Validate
    def _season_episodes(
        self,
        show_id: str,
        season_number: int,
    ) -> list[dict[str, Any]]:
        parsed = self.episodes_file(show_id, season_number).parsed()
        episodes: list[dict[str, Any]] = parsed["result"]["data"]
        return episodes

    # TODO: Validate
    def _movie_data(self, movie_id: str) -> dict[str, Any]:
        return self.movie_file(movie_id).parsed()

    # TODO: Validate
    def _series_title(self, show_id: str) -> str:
        first_season = self._season_numbers(show_id)[0]
        self.episodes_file(show_id, first_season).download_if_outdated()
        title: str = self._season_episodes(show_id, first_season)[0]["series_title"]
        return title

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        # Required to detect new seasons.
        return [self.show_page_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        # Required to detect new episodes.
        return [self.episodes_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        return [self.episodes_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
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
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode["content_id"]
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
