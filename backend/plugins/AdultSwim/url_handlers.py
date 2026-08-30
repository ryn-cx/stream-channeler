# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.AdultSwim import AdultSwim


# TODO: Validate
class AdultSwimURLHandler(URLHandler["AdultSwim"]):
    # TODO: Validate
    def __init__(self, plugin: AdultSwim, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


# TODO: Validate
class ShowURLHandler(AdultSwimURLHandler):
    _URL_REGEX = (
        r"\/(?!videos(?:$|[?#]|\/(?:$|[?#])))"
        r"(?:videos\/)?(?P<show_key>[a-z0-9-]+)\/?(?:$|[?#])"
    )

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_file(self._key),
            self.url,
        )


# TODO: Validate
class EpisodeURLHandler(AdultSwimURLHandler):
    """Adult Swim episode URL handler.

    Example URL https://www.adultswim.com/videos/toonami/the-return-episode-1
    """

    _URL_REGEX = r"\/videos\/(?P<episode_path>[a-z0-9-]+\/[a-z0-9-]+)(?:[\/?#]|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key.split("/")[0]

    # TODO: Validate
    @property
    def _episode_slug(self) -> str:
        return self._key.split("/")[1]

    # TODO: Validate
    def _episode_key(self) -> str | None:
        for season in self.plugin.show_file(self.show_key).parsed().seasons:
            for episode in season.episodes:
                if episode.slug == self._episode_slug:
                    return episode.id
        return None

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_file(self.show_key),
            self.url,
        )
        if self._episode_key() is None:
            msg = f"Invalid AdultSwim URL: {self.url}"
            raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        episode_key = self._episode_key()
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]
        return []
