# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from app.media.media_type import TMDBMediaType
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class BasePluginLinker(BasePluginCore, ABC):
    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        """Return the names on TMDB's provider list this plugin supports."""
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        """Return `True` if the the plugin supports the named provider from TMDB."""
        return provider_name in cls.name_on_tmdb()

    # TODO: Validate
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        """Return the TMDB lookup information for the given title."""
        if not title.name:
            msg = f"Title {title.key} has no name"
            raise ValueError(msg)

        media_type = (
            TMDBMediaType.movie
            if title.media_type == MediaType.movie
            else TMDBMediaType.tv
        )
        return [TMDBLookupInfo(title.name, media_type, title.year)]
