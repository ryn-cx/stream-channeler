# TODO: Validate
from typing import override
from urllib.parse import quote

from wholoo.movies.models import MoviesModel

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.Hulu.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = "movie" if show.media_type == "Movie" else "series"

    def _movie_model(self, movie_id: str) -> MoviesModel:
        return self.movie_file(movie_id).parsed()

    def _season_name(self, series_id: str, season_number: int) -> str:
        parsed = self.season_file(series_id, season_number).parsed()
        return parsed.series_grouping_metadata.grouping_name

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
            movie_entity = self._movie_model(show_key).details.entity
            return self._tmdb_search_media(movie_entity.name, MediaType.movie)
        self.series_file(show_key).download_if_outdated()
        entity = self._series_model(show_key).details.entity
        return self._tmdb_search_media(entity.name)

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_number = self._split_season_key(season_key)
        return season_number

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, season_number = self._split_season_key(season_key)
        for item in self._season_items(show_key, season_number):
            if str(item.id) == episode_key:
                return int(item.number)
        return None

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie() else MediaType.tv

    @classmethod
    def _show_url(cls, show_key: str, media_type: str) -> str:
        return cls.build_url(f"{media_type}/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    @staticmethod
    def _image_url(path: str) -> str:
        operations = quote('[{"resize":"600x600|max"},{"format":"webp"}]', safe=":,")
        return f"{path}&operations={operations}"
