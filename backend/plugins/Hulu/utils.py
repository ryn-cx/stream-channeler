# TODO: Validate
"""What every other part of the plugin reads a title by."""

from typing import override
from urllib.parse import quote, quote_plus

from wholoo.movies.models import MoviesModel

from app.shows.models import Show
from app.utils import tz_datetime
from plugins.Hulu.constants import (
    DETAIL_MAX_AGE,
    MOVIE_MEDIA_TYPE,
    SERIES_MEDIA_TYPE,
)
from plugins.Hulu.files import FileMixin
from plugins.utils.abstract_plugin import PluginShowIdentity


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
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @staticmethod
    def _image_url(path: str) -> str:
        operations = quote('[{"resize":"600x600|max"},{"format":"webp"}]', safe=":,")
        return f"{path}&operations={operations}"

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        if self._is_movie():
            return self._movie_identity(show_key)
        return self._series_identity(show_key)

    # TODO: Validate
    def _movie_identity(self, movie_id: str) -> PluginShowIdentity:
        movie_file = self.movie_file(movie_id)
        movie_file.download_if_outdated(tz_datetime.now() - DETAIL_MAX_AGE)
        model = movie_file.parsed()
        return PluginShowIdentity(
            title=model.name,
            media_type="Movie",
            year=model.details.entity.premiere_date.year,
        )

    # TODO: Validate
    def _series_identity(self, series_id: str) -> PluginShowIdentity:
        series_file = self.series_file(series_id)
        series_file.download_if_outdated(tz_datetime.now() - DETAIL_MAX_AGE)
        model = series_file.parsed()
        return PluginShowIdentity(
            title=model.name,
            media_type="Series",
            year=model.details.entity.premiere_date.year,
        )
