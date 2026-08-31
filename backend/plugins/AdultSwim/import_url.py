# TODO: Validate
from __future__ import annotations

import re
from typing import override

from app.shows.models import Show
from plugins.AdultSwim.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, ReadURLPlugin, register=False):
    # https://www.adultswim.com/videos/toonami/the-return-episode-1
    _EPISODE_URL_REGEX = (
        r"\/videos\/(?P<episode_path>[a-z0-9-]+\/[a-z0-9-]+)(?:[\/?#]|$)"
    )
    _SHOW_URL_REGEX = (
        r"\/(?!videos(?:$|[?#]|\/(?:$|[?#])))"
        r"(?:videos\/)?(?P<show_key>[a-z0-9-]+)\/?(?:$|[?#])"
    )

    _episode_key: str | None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._EPISODE_URL_REGEX, cls._SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        self._episode_key = None

        if match := re.match(domain_regex + self._EPISODE_URL_REGEX, url):
            show_key, episode_slug = match.group("episode_path").split("/")
            self._show_key = show_key
            self.raise_if_invalid_file(self.show_file(show_key), url)
            self._episode_key = self._episode_key_for_slug(episode_slug)
            if self._episode_key is None:
                msg = f"Invalid {self.plugin_key()} URL: {url}"
                raise InvalidURLError(msg)
            return

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            self._show_key = match.group("show_key")
            self.raise_if_invalid_file(self.show_file(self._show_key), url)
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _episode_key_for_slug(self, episode_slug: str) -> str | None:
        for season in self.show_file(self._show_key).parsed().seasons:
            for episode in season.episodes:
                if episode.slug == episode_slug:
                    return episode.id
        return None

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]
        return []
