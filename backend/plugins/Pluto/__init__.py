# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from typing import override

from plugins.Pluto.import_url import ImportURLMixin
from plugins.Pluto.upsert import UpsertMixin


# TODO: Validate
class Pluto(
    UpsertMixin,
    ImportURLMixin,
    register=True,
):
    """Pluto TV plugin."""

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Pluto TV",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"
