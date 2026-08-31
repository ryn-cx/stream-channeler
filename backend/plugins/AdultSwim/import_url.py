# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.shows.models import Show
from plugins.AdultSwim.base import AdultSwimBase
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin_v2.workers import URLImporter

if TYPE_CHECKING:
    from collections.abc import Iterable


# TODO: Validate
class AdultSwimImportURL(URLImporter, AdultSwimBase):
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
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            self._show_key = match.group("show_key")
            self.raise_if_invalid_file(self.show_file(self._show_key), url)
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
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

    # TODO: Validate
    @override
    def import_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        shows = self._existing_shows(show_key)

        # If the show already exists and an update is not required just return the
        # import results.
        if shows and not force:
            return self._results_for_shows(shows)

        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            shows = self._existing_shows(show_key)
            if shows and not force:
                return self._results_for_shows(shows)

        return self._results_for_shows(
            [
                self.upsert_show(source, show_key, canonical_show, force=force)
                for source in self._sources.values()
            ],
        )

    # TODO: Validate
    def _results_for_shows(self, shows: Iterable[Show]) -> list[URLImportResult]:
        return [result for show in shows for result in self._import_results(show)]
