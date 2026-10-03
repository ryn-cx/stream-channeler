# TODO: Validate
"""What the plugin, its importers and its initializer all read Disney+ by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from plugins.DisneyPlus.constants import ENTITY_URL_REGEX
from plugins.DisneyPlus.files import Entity
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kneeminus.entity.models import EntityModel

    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class DisneyPlusShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"browse/entity-{title_key}")

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"

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
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    def entity_file(self, entity_id: str) -> Entity:
        return self._cached_file(Entity, entity_id)

    # TODO: Validate
    def _url_title_key(self, url: str) -> str:
        if not (match := re.match(self._domains_regex() + ENTITY_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return match.group("title_key")

    # TODO: Validate
    @staticmethod
    def is_movie(entity: EntityModel) -> bool:
        return not entity.seasons and entity.series_title is None


# TODO: Validate
class DisneyPlusImporter(DisneyPlusShared, BaseUpserter, ABC):
    # TODO: Validate
    def _entity(self, title_key: str) -> EntityModel:
        return self.entity_file(title_key).parsed()

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons.
        return [self.entity_file(title_key)]

    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_id: str) -> str:
        return f"{title_key}:{season_id}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, str]:
        title_key, _, season_id = season_key.partition(":")
        return title_key, season_id

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        title_key = self._url_title_key(url)
        self.raise_invalid_url_if_no_content(self.entity_file(title_key), url)
        return ParsedURL(title_key)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        entity = self._entity(title.key)
        self.add_title_to_channel("All Titles", title)
        self.add_new_urls_to_channel("All Titles", self.recommendation_urls(entity))
        media_type_name = "Movies" if self.is_movie(entity) else "Series"
        self.set_title_tag_channels(title, [media_type_name, *entity.genres])

    # TODO: Validate
    def _background_image_url(self, title_key: str) -> str:
        return self.background_image_url(self._entity(title_key))

    # TODO: Validate
    def _background_thumbnail_url(self, title_key: str) -> str:
        return self.background_thumbnail_url(self._entity(title_key))

    # TODO: Validate
    @staticmethod
    def required_value[ValueT](value: ValueT | None, description: str) -> ValueT:
        """Return `value`, raising when the page left it out."""
        if value is None:
            msg = f"The page has no {description}."
            raise ValueError(msg)
        return value

    # TODO: Validate
    @classmethod
    def video_url(cls, episode_id: str) -> str:
        return cls.build_url(f"play/{episode_id}")

    # TODO: Validate
    @classmethod
    def background_image_url(cls, entity: EntityModel) -> str:
        return cls.required_value(entity.background_image, "background image").url

    # TODO: Validate
    @classmethod
    def background_thumbnail_url(cls, entity: EntityModel) -> str:
        return cls.required_value(
            entity.background_image,
            "background image",
        ).thumbnail_url

    # TODO: Validate
    @classmethod
    def recommendation_urls(cls, entity: EntityModel) -> list[str]:
        return [
            cls.title_url(str(recommendation.entity_id))
            for recommendation in entity.recommendations
        ]
