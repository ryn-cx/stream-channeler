# TODO: Validate
"""Disney+ plugin.

There is no obvious way to get information on episodes after episode 24, so a
long running series is only read as far as that.
"""

from __future__ import annotations

from typing import override

from plugins.DisneyPlus.import_url import ImportURLMixin
from plugins.DisneyPlus.source import SourceMixin
from plugins.DisneyPlus.upsert import UpsertMixin


# TODO: Validate
class DisneyPlus(
    UpsertMixin,
    SourceMixin,
    ImportURLMixin,
    # Temporarily disabled until a solution is found to get episodes past episode 24
    register=True,
):
    """Disney+ plugin."""

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Disney+",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.disneyplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"
