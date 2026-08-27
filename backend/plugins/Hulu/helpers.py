# TODO: Validate
"""What every other part of the plugin reads a title by."""

from typing import override
from urllib.parse import quote, quote_plus

from wholoo.movies.models import MoviesModel

from app.shows.models import Show
from plugins.Hulu.constants import (
    MEDIA_IDENTIFIER_SEPARATOR,
    MOVIE_MEDIA_TYPE,
    SERIES_MEDIA_TYPE,
)
from plugins.Hulu.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and what a search result of it is asked for by."""

    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = (
            MOVIE_MEDIA_TYPE if show.media_type == "Movie" else SERIES_MEDIA_TYPE
        )

    # TODO: Validate
    def _movie_model(self, movie_id: str) -> MoviesModel:
        return self.movie_file(movie_id).parsed()

    # TODO: Validate
    def _season_name(self, series_id: str, season_number: int) -> str:
        parsed = self.season_file(series_id, season_number).parsed()
        return parsed.series_grouping_metadata.grouping_name

    # TODO: Validate
    @staticmethod
    def media_identifier(media_type: str, title_key: str) -> str:
        """Return what a search result of `title_key` is asked back for by.

        Hulu names a film and a series the same way, so which of the two the id
        belongs to is written alongside it.
        """
        return f"{media_type}{MEDIA_IDENTIFIER_SEPARATOR}{title_key}"

    # TODO: Validate
    @staticmethod
    def split_media_identifier(media_identifier: str) -> tuple[str, str]:
        """Return the media type and the id `media_identifier` was built from."""
        media_type, _, title_key = media_identifier.partition(
            MEDIA_IDENTIFIER_SEPARATOR,
        )
        return media_type, title_key

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str, media_type: str) -> str:
        return cls.build_url(f"{media_type}/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @staticmethod
    def _image_url(path: str) -> str:
        operations = quote('[{"resize":"600x600|max"},{"format":"webp"}]', safe=":,")
        return f"{path}&operations={operations}"
