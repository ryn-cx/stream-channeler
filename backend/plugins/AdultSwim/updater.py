# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.AdultSwim.constants import FREE, SUBSCRIPTION
from plugins.AdultSwim.files import TitlesPage
from plugins.AdultSwim.shared import AdultSwimShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class AdultSwimUpdater(AdultSwimShared, BasePluginUpdater):
    def titles_page_file(self) -> TitlesPage:
        return self._cached_file(TitlesPage)

    @override
    def _plugin_files(self) -> Sequence[TitlesPage]:
        # This is a plugin file and not a source file because Adult Swim has 2 seperates
        # sources, one for free content and one for paid content.
        return [self.titles_page_file()]

    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (FREE, SUBSCRIPTION)

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return [
            self.title_url(title_key)
            for title_key in self._title_keys_from_plugin_files()
        ]

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        return [
            show.slug
            for show in self.titles_page_file().parsed().shows
            if show.slug is not None
        ]
