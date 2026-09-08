# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.importer import (
    NetflixImporter,
    NetflixMovieImporter,
    NetflixSeriesImporter,
)
from plugins.Netflix.shared import NetflixShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


class NetflixInitializer(BasePluginInitializer, NetflixShared): ...


# TODO: Validate
class Netflix(NetflixShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = NetflixInitializer

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    @override
    def _media_importer_from_url(self, url: str) -> NetflixImporter:
        if not (match := re.match(self._domain_regex() + TITLE_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        # Movies and series use the same URL format and the same title_file, but the
        # title_file contains the media type information.
        title_key = match.group("title_key")
        self.raise_invalid_url_if_no_content(self.title_file(title_key), url)
        if self.title_file(title_key).title_information().field__typename == "Movie":
            return NetflixMovieImporter(self)
        return NetflixSeriesImporter(self)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> NetflixImporter:
        if not title.media_type:  # Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == "Movie":
            return NetflixMovieImporter(self)
        return NetflixSeriesImporter(self)

    # TODO: Validate
    @override
    def search_for_title_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.search_file(names[0])
        for section in search_file.parsed().data.page.sections.edges:
            for entity in section.node.entities.edges:
                unified_entity = entity.node.unified_entity
                if unified_entity.field__typename in {"Title", "Movie"}:
                    return self.title_url(str(unified_entity.video_id))
        return None
