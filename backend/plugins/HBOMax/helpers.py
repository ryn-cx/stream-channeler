# TODO: Validate
from typing import override
from urllib.parse import quote

from minbo.movies.models import Idref14 as MovieContent

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.HBOMax.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = "movie" if show.media_type == "Movie" else "series"

    # TODO: Validate
    def _movie_content(self, movie_id: str) -> MovieContent:
        return self.movie_file(movie_id).parsed().props.page_props.mapped_data.idref14

    # TODO: Validate
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        if self._is_movie():
            self.movie_file(show_key).download_if_outdated()
            movie = self._movie_content(show_key)
            return self._tmdb_search_media(movie.title.full, MediaType.movie)
        self.show_file(show_key).download_if_outdated()
        show = self._show_content(show_key)
        return self._tmdb_search_media(show.title.full)

    # TODO: Validate
    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_number = self._split_season_key(season_key)
        return season_number

    # TODO: Validate
    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, episode_number = self._split_episode_key(episode_key)
        return episode_number

    # TODO: Validate
    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie() else MediaType.tv

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
