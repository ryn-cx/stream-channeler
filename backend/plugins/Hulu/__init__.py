# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from typing import override

from plugins.Hulu.channels import ChannelMixin
from plugins.Hulu.import_url import ImportURLMixin
from plugins.Hulu.source import SourceMixin
from plugins.Hulu.upsert import UpsertMixin
from plugins.utils.base_plugin.search import CatalogueSearchMixin


# TODO: Validate
class Hulu(
    UpsertMixin,
    CatalogueSearchMixin,
    SourceMixin,
    ChannelMixin,
    ImportURLMixin,
    register=True,
):
    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Hulu",)

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"
