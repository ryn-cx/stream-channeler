# TODO: Validate
"""Tubi URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Tubi.constants import CONTENT_ID_REGEX, SLUG_REGEX
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.Tubi import Tubi


# TODO: Validate
class TubiURLHandler(URLHandler["Tubi"]):
    """What every Tubi URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: Tubi, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.content_file(self._key),
            self.url,
        )


# TODO: Validate
class MovieURLHandler(TubiURLHandler):
    """Tubi movie URL handler.

    Example URL https://tubitv.com/movies/100029837/megamind
    """

    _URL_REGEX = rf"\/movies\/(?P<movie_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"


# TODO: Validate
class SeriesURLHandler(TubiURLHandler):
    """Tubi series URL handler.

    Example URL https://tubitv.com/series/300006854/scooby-doo-where-are-you
    """

    _URL_REGEX = rf"\/series\/(?P<series_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"


# TODO: Validate
class EpisodeURLHandler(TubiURLHandler):
    """Tubi episode URL handler.

    Example URL https://tubitv.com/tv-shows/595036/s01-e01-what-a-night-for-a-knight
    """

    _URL_REGEX = rf"\/tv-shows\/(?P<episode_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        series_id = self.plugin.content_file(self._key).parsed().series_id
        if series_id is None:
            msg = f"Invalid Tubi URL: {self.url}"
            raise InvalidURLError(msg)
        return series_id

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._key:
                    return [
                        URLImportResult.for_episodes(show, [episode]),
                    ]

        msg = f"Episode {self._key} not found in show {show.key}"
        raise InvalidURLError(msg)
