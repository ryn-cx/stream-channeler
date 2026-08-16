# TODO: Validate
"""Hulu URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.files import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.Hulu import Hulu

_UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SLUG_REGEX = r"(?:[a-z0-9-]+-)?"


# TODO: Validate
class HuluURLHandler(MediaTypeURLHandler["Hulu"]):
    """What every Hulu URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: Hulu, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key


# TODO: Validate
class SeriesURLHandler(HuluURLHandler):
    """Hulu series URL handler.

    Example URL https://www.hulu.com/series/fdeb1018-4472-442f-ba94-fb087cdea069
    """

    media_type = SERIES_MEDIA_TYPE
    # The title slug in front of the id is decorative, only the id matters.
    # https://www.hulu.com/series/rick-and-morty-4e0f6374-fc81-4da2-b7a9-f7f8c29e7acc
    _URL_REGEX = rf"\/series\/{_SLUG_REGEX}(?P<series_id>{_UUID_REGEX})"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.series_file(self._key),
            self.url,
        )


# TODO: Validate
class WatchURLHandler(HuluURLHandler):
    """Hulu episode URL handler.

    Example URL https://www.hulu.com/watch/60da223c-d2a0-411a-95c9-665a839371f9
    """

    media_type = SERIES_MEDIA_TYPE
    # A watch URL points at a single episode, so the series it belongs to has to be
    # looked up before the show can be imported.
    _URL_REGEX = rf"\/watch\/(?P<episode_id>{_UUID_REGEX})"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self.plugin.episode_hub_file(self._key).series_id()

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.episode_hub_file(self._key),
            self.url,
        )


# TODO: Validate
class MovieURLHandler(HuluURLHandler):
    """Hulu movie URL handler.

    Example URL https://www.hulu.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981
    """

    media_type = MOVIE_MEDIA_TYPE
    # https://www.hulu.com/movie/the-wolf-of-wallstreet-4ee4f57e-19bd-493f-96f9-ad3e753af981
    _URL_REGEX = rf"\/movie\/{_SLUG_REGEX}(?P<movie_id>{_UUID_REGEX})"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
