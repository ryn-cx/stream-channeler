"""Crunchyroll URL handlers."""
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.Crunchyroll import Crunchyroll


class CrunchyrollURLHandler(URLHandler["Crunchyroll"]):
    """Base URL handler for the Crunchyroll plugin."""

    @override
    def __init__(self, plugin: Crunchyroll, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class CrunchyrollSeriesURLHandler(CrunchyrollURLHandler):
    """Crunchyroll series URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/series/GEXH3W29Z
        - https://www.crunchyroll.com/series/GEXH3W29Z/compass20-animation-project
    """

    _URL_REGEX = r"\/series\/(?P<show_key>[A-Z0-9]{9,})(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def raise_if_invalid(self) -> None:
        plugin_file = self.plugin.series_file(self._key)
        self.plugin.raise_if_invalid_file(plugin_file, self.url)


class CrunchyrollEpisodeURLHandler(CrunchyrollURLHandler):
    """Crunchyroll episode URL handler.

    Supported URL Formats:
        - https://www.crunchyroll.com/watch/GVWU8XW1Z
        - https://www.crunchyroll.com/watch/GVWU8XW1Z/this-is-compass20
    """

    _URL_REGEX = r"\/watch\/(?P<episode_key>[A-Z0-9]{9,})(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        objects_file = self.plugin.objects_file(self._key)
        return objects_file.parsed().data[0].episode_metadata.series_id

    @override
    def raise_if_invalid(self) -> None:
        objects_file = self.plugin.objects_file(self._key)
        self.plugin.raise_if_invalid_file(objects_file, self.url)

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._key:
                    return [
                        URLImportResult(
                            show=show,
                            episodes=[episode],
                            is_whitelist=True,
                        ),
                    ]

        msg = f"Episode {self._key} not found in show {show.key}"
        raise InvalidURLError(msg)
