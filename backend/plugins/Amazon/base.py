# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Amazon.search import SearchMixin
from plugins.Amazon.source import SourceMixin
from plugins.Amazon.upsert import UpsertMixin


# TODO: Validate
class AmazonBase(UpsertMixin, SearchMixin, SourceMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon Prime Video"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Amazon Prime Video", "Amazon Video", "Prime Video")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        # Prime Video is read out of its own website, and Amazon's is listed as
        # well because a link to a title on it is a link to the same title.
        # watch.amazon.com is the domain Amazon writes a share link under, and
        # is its own entry because only an optional `www.` is read off a domain.
        return ["primevideo.com", "amazon.com", "watch.amazon.com"]

    # TODO: Validate
    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.endswith("Amazon Channel")
