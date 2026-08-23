# TODO: Validate
"""What every other part of the plugin reads a title by."""

from typing import override
from urllib.parse import quote

from app.shows.models import Show
from plugins.HBOMax.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and which kind of title is being read."""

    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = "movie" if show.media_type == "Movie" else "series"

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"show/{show_key}")

    # TODO: Validate
    @classmethod
    def _movie_url(cls, movie_key: str) -> str:
        return cls.build_url(f"movie/{movie_key}")

    # TODO: Validate
    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search/result?q={quote(query)}")
