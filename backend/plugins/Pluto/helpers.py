# TODO: Validate
"""The URLs of a title and what kind of title it is."""

from typing import override
from urllib.parse import quote

from app.shows.models import Show
from plugins.Pluto.constants import LOCALE
from plugins.Pluto.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs Pluto TV writes a title under."""

    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = "movie" if show.media_type == "Movie" else "series"

    # TODO: Validate
    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/series/{show_key}/details")

    # TODO: Validate
    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/movies/{show_key}/details")

    # TODO: Validate
    @classmethod
    def _season_url(cls, show_key: str, season_number: int) -> str:
        return cls.build_url(
            f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}",
        )

    # TODO: Validate
    @classmethod
    def _episode_url(
        cls,
        show_key: str,
        season_number: int,
        episode_key: str,
    ) -> str:
        return cls.build_url(
            f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}"
            f"/episode/{episode_key}",
        )

    # TODO: Validate
    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"{LOCALE}/search?query={quote(query)}")
