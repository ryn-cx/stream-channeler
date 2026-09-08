# TODO: Validate
from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.Crunchyroll.base_files import CrunchyrollBaseFiles
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE
from plugins.Crunchyroll.utils import build_url


# TODO: Validate
class CrunchyrollShared(CrunchyrollBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str:
        return build_url(f"search?q={quote_plus(query)}")
