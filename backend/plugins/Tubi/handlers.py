# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.Tubi import Tubi

_CONTENT_ID_REGEX = r"\d+"
# Every title path ends with an optional slug, e.g. /megamind or /season-1.
_SLUG_REGEX = r"(?:\/[^\/?#]*)?"


class TubiURLHandler(URLHandler["Tubi"]):
    def __init__(self, plugin: Tubi, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        return self._key

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.content_file(self._key),
            self.url,
        )


class MovieURLHandler(TubiURLHandler):
    # https://tubitv.com/movies/100029837/megamind
    _PATH_REGEX = rf"\/movies\/(?P<movie_id>{_CONTENT_ID_REGEX}){_SLUG_REGEX}(?:\/|$)"


class SeriesURLHandler(TubiURLHandler):
    # https://tubitv.com/series/300006854/scooby-doo-where-are-you
    _PATH_REGEX = rf"\/series\/(?P<series_id>{_CONTENT_ID_REGEX}){_SLUG_REGEX}(?:\/|$)"


class EpisodeURLHandler(TubiURLHandler):
    # https://tubitv.com/tv-shows/595036/s01-e01-what-a-night-for-a-knight
    _PATH_REGEX = (
        rf"\/tv-shows\/(?P<episode_id>{_CONTENT_ID_REGEX}){_SLUG_REGEX}(?:\/|$)"
    )

    @property
    @override
    def show_key(self) -> str:
        series_id = self.plugin.content_file(self._key).parsed().series_id
        if series_id is None:
            msg = f"Invalid Tubi URL: {self.url}"
            raise InvalidURLError(msg)
        return series_id

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
