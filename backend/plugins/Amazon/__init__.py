# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.Amazon.constants import (
    AMAZON_URL_REGEX,
    MOVIE_ENTITY_TYPE,
    PRIME_VIDEO_URL_REGEX,
    SHARE_URL_REGEX,
)
from plugins.Amazon.importer import (
    AmazonImporter,
    AmazonMovieImporter,
    AmazonSeriesImporter,
)
from plugins.Amazon.shared import AmazonShared
from plugins.Amazon.utils import detail_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class AmazonInitializer(BasePluginInitializer, AmazonShared): ...


# TODO: Validate
class Amazon(AmazonShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = AmazonInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            # Must be listed first: a share link's path is also a detail path, and
            # only this one carries the id in the query rather than the path.
            SHARE_URL_REGEX,
            PRIME_VIDEO_URL_REGEX,
            AMAZON_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        title_key = self._url_title_key(url)
        self.raise_invalid_url_if_no_content(self.detail_file(title_key), url)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> AmazonImporter:
        # A film and a season of a series are answered at the same address,
        # so the page has to be read before it is known which of the two it
        # is.
        if self._is_movie(self._url_title_key(url)):
            return AmazonMovieImporter(self)
        return AmazonSeriesImporter(self)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> AmazonImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return AmazonMovieImporter(self)
        return AmazonSeriesImporter(self)

    # TODO: Validate
    def _url_title_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SHARE_URL_REGEX, url):
            return self.title_key_from_share_key(
                match.group("watch_amazon_title_key"),
            )
        if match := re.match(domain_regex + PRIME_VIDEO_URL_REGEX, url):
            return match.group("prime_video_title_key")
        if match := re.match(domain_regex + AMAZON_URL_REGEX, url):
            return match.group("amazon_title_key")

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def search_for_title_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.search_file(names[0])
        search_file.download_if_outdated()
        results = search_file.results()
        return detail_url(results[0]) if results else None

    # TODO: Validate
    def _is_movie(self, title_key: str) -> bool:
        return self.detail_file(title_key).entity_type() == MOVIE_ENTITY_TYPE
