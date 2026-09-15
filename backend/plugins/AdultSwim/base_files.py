# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from plugins.AdultSwim.files import TitlePage, TitlesPage
from plugins.AdultSwim.utils import episode_keys, season_keys
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AdultSwimBaseFiles(BasePlugin):
    # TODO: Validate
    def title_file(self, title_key: str) -> TitlePage:
        return self._cached_file(TitlePage, title_key)

    # TODO: Validate
    def titles_file(self) -> TitlesPage:
        return self._cached_file(TitlesPage)

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[TitlesPage]:
        return [self.titles_file()]

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[TitlesPage]:
        return [self.titles_file()]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return season_keys(self.title_file(title_key).parsed())

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return episode_keys(self.title_file(title_key).parsed(), season_keys)
