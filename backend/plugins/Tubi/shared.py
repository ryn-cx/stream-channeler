# TODO: Validate
"""What the plugin, its importers and its initializer all read Tubi by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from plugins.Tubi.constants import EPISODE_URL_REGEX, MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Tubi.files import ContentFile
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugi.content.models import Child as SeasonChild
    from plugi.content.models import Child1 as EpisodeChild
    from plugi.content.models import ContentModel

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://tubitv.com/{path.lstrip('/')}"


# TODO: Validate
def series_url(title_key: str) -> str:
    return build_url(f"series/{title_key}")


# TODO: Validate
def movie_url(title_key: str) -> str:
    return build_url(f"movies/{title_key}")


# TODO: Validate
def episode_url(episode_key: str) -> str:
    return build_url(f"tv-shows/{episode_key}")


# TODO: Validate
def episode_name(title: str) -> str:
    # Episode titles are prefixed with their season and episode number,
    # e.g. "S01:E01 - What a Night for a Knight".
    return re.sub(r"^S\d+:E\d+ - ", "", title)


# TODO: Validate
def first_image(images: list[str]) -> str | None:
    return images[0] if images else None


# TODO: Validate
def is_movie(content: ContentModel) -> bool:
    # The `type` field of a Tubi content response marks a series; a movie
    # and a single episode both use "v".
    return content.type != "s"


# TODO: Validate
def build_season_key(title_key: str, season_id: str) -> str:
    """Encode the title key into the season key.

    Every entity's data comes from the single content file keyed by the title,
    but the base plugin resolves episode files from a season key alone, so the
    title key is carried inside it.
    """
    return f"{title_key}:{season_id}"


# TODO: Validate
def movie_season_key(title_key: str) -> str:
    # A movie has no seasons of its own so its single season is given a
    # fixed id.
    return build_season_key(title_key, "0")


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, season_id = season_key.partition(":")
    return title_key, season_id


# TODO: Validate
def seasons(content: ContentModel) -> list[SeasonChild]:
    children = content.children
    if children is None:
        return []
    # Tubi returns the seasons in an arbitrary order.
    return sorted(children, key=lambda season: int(season.id))


# TODO: Validate
def season_episodes(content: ContentModel, season_id: str) -> list[EpisodeChild]:
    for season in seasons(content):
        if season.id == season_id:
            return season.children
    return []


# TODO: Validate
class TubiShared(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Tubi"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._cached_file(ContentFile, content_id)

    # TODO: Validate
    def _content(self, title_key: str) -> ContentModel:
        return self.content_file(title_key).parsed()


# TODO: Validate
class TubiImporter(TubiShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the title's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]
