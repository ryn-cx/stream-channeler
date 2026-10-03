# TODO: Validate
"""What the plugin, its importers and its initializer all read Peacock by."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, override

from plugins.Peacock.constants import EPISODE_URL_REGEX, TITLE_URL_REGEX
from plugins.Peacock.files import MovieFile
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from pigeon.movie.models import Image as MovieImage
    from pigeon.show.models import Image as ShowImage

    from app.titles.models import Title


# TODO: Validate
class PeacockShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def build_url(cls, path: str) -> str:
        return f"https://www.peacocktv.com/{path.lstrip('/')}"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Peacock"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.peacocktv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "peacocktv.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._cached_file(MovieFile, movie_id)

    # TODO: Validate
    @classmethod
    def asset_url(cls, slug: str) -> str:
        """Return the watch page of the node `slug` names."""
        return cls.build_url(f"watch/asset/{slug.lstrip('/')}")

    # TODO: Validate
    @staticmethod
    def is_series_key(title_key: str) -> bool:
        """Return whether `title_key` can only belong to a series.

        A movie is always keyed by a UUID, so a numeric key names a series while a
        UUID has to be looked up before it is known which of the two it is.
        """
        return title_key.isdigit()


# TODO: Validate
class PeacockImporter(PeacockShared, BaseUpserter, ABC):
    # TODO: Validate
    @abstractmethod
    def _media_type_channel_key(self) -> str: ...

    # TODO: Validate
    @abstractmethod
    def _genres(self, title_key: str) -> list[str]: ...

    # TODO: Validate
    @abstractmethod
    def _recommendation_urls(self, title_key: str) -> list[str]: ...

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        self.add_title_to_channel("All Titles", title)
        self.add_new_urls_to_channel("All Titles", self._recommendation_urls(title.key))
        self.set_title_tag_channels(
            title,
            [self._media_type_channel_key(), *self._genres(title.key)],
        )

    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_id: str) -> str:
        """Encode the title key into the season key.

        Every entity's data comes from the single show file keyed by the series, but
        the base plugin resolves episode files from a season key alone, so the title
        key is included inside it.
        """
        return f"{title_key}:{season_id}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, str]:
        title_key, _, season_id = season_key.partition(":")
        return title_key, season_id

    # TODO: Validate
    @staticmethod
    def image_url(
        images: list[ShowImage] | list[MovieImage],
        image_type: str,
    ) -> str | None:
        for image in images:
            if image.type == image_type:
                return image.url
        return None

    # TODO: Validate
    @classmethod
    def landscape_url(cls, images: list[ShowImage] | list[MovieImage]) -> str | None:
        return cls.image_url(images, "landscape")

    # TODO: Validate
    @classmethod
    def poster_url(cls, images: list[ShowImage] | list[MovieImage]) -> str | None:
        return cls.image_url(images, "titleArt34")
