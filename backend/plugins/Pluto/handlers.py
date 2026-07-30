# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.Pluto import Pluto

_ITEM_ID_REGEX = r"[0-9a-f]{24}"
# Optional locale segment, e.g. /en, /us or /en-gb.
_LOCALE_REGEX = r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"
# Optional suffix the website adds to the canonical URL of a title.
_DETAILS_REGEX = r"(?:\/details)?"
# Optional segments of a link that points at a season or an episode of a series.
_SEASON_REGEX = rf"(?:\/season\/\d+(?:\/episode\/{_ITEM_ID_REGEX})?)?"


class PlutoURLHandler(MediaTypeURLHandler["Pluto"]):
    def __init__(self, plugin: Pluto, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        return self._key


class MovieURLHandler(PlutoURLHandler):
    media_type = "movie"
    # https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details
    # https://pluto.tv/us/on-demand/movies/68a54f49df1220b53566f16e
    _PATH_REGEX = (
        rf"{_LOCALE_REGEX}\/on-demand\/movies\/(?P<movie_id>{_ITEM_ID_REGEX})"
        rf"{_DETAILS_REGEX}(?:\/|$)"
    )

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.items_file(self._key),
            self.url,
        )


class SeriesURLHandler(PlutoURLHandler):
    media_type = "series"
    # https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1
    # https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1/episode/5ef05c6ecdce3c001a779a95
    _PATH_REGEX = (
        rf"{_LOCALE_REGEX}\/on-demand\/series\/(?P<series_id>{_ITEM_ID_REGEX})"
        rf"{_SEASON_REGEX}{_DETAILS_REGEX}(?:\/|$)"
    )

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.seasons_file(self._key),
            self.url,
        )
