from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.Netflix.base_files import NetflixBaseFiles


class NetflixShared(NetflixBaseFiles):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Netflix"

    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Netflix", "Netflix Standard with Ads")

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.netflix.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    @classmethod
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"title/{title_key}")

    @classmethod
    def episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")
