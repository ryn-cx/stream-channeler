# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.IMDb.constants import TITLE_URL_REGEX
from plugins.utils.base_plugin.core import BasePluginCore


# TODO: Validate
class IMDbShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "IMDb"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str | None:
        return "https://www.imdb.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domains(cls) -> list[str]:
        return ["imdb.com", "m.imdb.com"]

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)
