# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from typing import Any, override

from pools_closed import PoolsClosed
from pools_closed.exceptions import ShowNotFoundError
from pools_closed.show import Show as ShowEndpoint
from pools_closed.show.models import ShowModel
from pools_closed.shows import Shows as ShowsEndpoint
from pools_closed.shows.models import ShowsModel
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


@cache
def pools_closed() -> PoolsClosed:
    return PoolsClosed(get_around_client=get_around_client())


class ShowPage(EndpointFile[ShowModel]):
    @override
    def _endpoint(self) -> ShowEndpoint:
        return pools_closed().show

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


class ShowsPage(EndpointFile[ShowsModel]):
    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        super().__init__(session, plugin, "Shows")

    @override
    def _endpoint(self) -> ShowsEndpoint:
        return pools_closed().shows

    # Required because the endpoint takes no parameters
    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


# TODO: Validate
class FileMixin(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def _plugin_wide_files(cls) -> tuple[type[BaseFile[Any]], ...]:
        return (ShowsPage,)

    # TODO: Validate
    def show_file(self, show_key: str) -> ShowPage:
        return self._file(ShowPage, show_key)

    # TODO: Validate
    def shows_file(self) -> ShowsPage:
        return self._file(ShowsPage)

    # TODO: Validate
    @classmethod
    def show_url(cls, show_key: str) -> str:
        return cls.build_url(f"videos/{show_key}")

    # TODO: Validate
    @classmethod
    def episode_url(cls, show_key: str, episode_slug: str) -> str:
        return cls.build_url(f"videos/{show_key}/{episode_slug}")

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[ShowsPage]:
        return [self.shows_file()]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            str(season.number) for season in self.show_file(show_key).parsed().seasons
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
        return [
            episode.id
            for season in self.show_file(show_key).parsed().seasons
            if str(season.number) in season_keys
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def get_tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo:
        show_page = self.show_file(show_key)
        show_page.download_if_outdated()
        return TMDBLookupInfo(
            title=show_page.parsed().title,
            media_type="TV Show",
        )
