# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.Roku.constants import CONTENT_ID_REGEX
from plugins.Roku.files import content_id
from plugins.Roku.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, ReadURLPlugin, register=False):
    # https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae
    # The title slug after the content id is decorative, only the id matters.
    _DETAILS_URL_REGEX = (
        rf"\/details\/(?P<details_content_id>{CONTENT_ID_REGEX})"
        r"(?:\/[^\/?#]+)?(?:\/|$)"
    )
    # https://therokuchannel.roku.com/watch/db1607f1cff2522bb795382bb4b5bcae
    _WATCH_URL_REGEX = rf"\/watch\/(?P<watch_content_id>{CONTENT_ID_REGEX})(?:\/|$)"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._DETAILS_URL_REGEX, cls._WATCH_URL_REGEX)

    # TODO: Validate
    @override
    def _read_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                key = match.group(1)
                self.raise_if_invalid_file(self.content_file(key), url)
                # A season or an episode URL is imported as the series it belongs to.
                if series := self.content_file(key).parsed().series:
                    self._show_key = content_id(series.meta.id)
                else:
                    self._show_key = key
                return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)
