# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Roku.base import RokuBase
from plugins.Roku.constants import CONTENT_ID_REGEX
from plugins.Roku.files import content_id
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin_v2.importer import BaseImporter

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class RokuImporter(BaseImporter, RokuBase):
    # https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae
    # The title slug after the content id is decorative, only the id matters.
    _DETAILS_URL_REGEX = (
        rf"\/details\/(?P<details_content_key>{CONTENT_ID_REGEX})"
        r"(?:\/[^\/?#]+)?(?:\/|$)"
    )
    # https://therokuchannel.roku.com/watch/db1607f1cff2522bb795382bb4b5bcae
    _WATCH_URL_REGEX = rf"\/watch\/(?P<watch_content_key>{CONTENT_ID_REGEX})(?:\/|$)"

    _episode_key: str | None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._DETAILS_URL_REGEX, cls._WATCH_URL_REGEX)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        self._episode_key = None
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                key = match.group(1)
                self.raise_if_invalid_file(self.content_file(key), url)
                # A season or an episode URL is imported as the series it belongs to.
                if series := self.content_file(key).parsed().series:
                    if "-" not in key:
                        self._episode_key = key
                    return content_id(series.meta.id)
                return key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]

        msg = f"Episode {self._episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)
