# TODO: Validate
from __future__ import annotations

from abc import ABC

from app.media.media_type import TMDBMediaType
from app.titles.models import Title
from app.tmdb_media.tmdb import get_media_type_and_tmdb_id
from plugins.TMDB.files import IMDbTitle, MoviesExternalIds, TVSeriesExternalIds
from plugins.TMDB.shared import TMDBImporter


# TODO: Validate
class TMDBIMDbImporter(TMDBImporter, ABC):
    # TODO: Validate
    def movies_external_ids_file(self, tmdb_movie_id: int) -> MoviesExternalIds:
        return self._cached_file(MoviesExternalIds, tmdb_movie_id)

    # TODO: Validate
    def tv_series_external_ids_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesExternalIds:
        return self._cached_file(TVSeriesExternalIds, tmdb_tv_title_id)

    # TODO: Validate
    def external_ids_file(
        self,
        tmdb_title_key: str,
    ) -> MoviesExternalIds | TVSeriesExternalIds:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(tmdb_title_key)
        if media_type == TMDBMediaType.movie:
            return self.movies_external_ids_file(tmdb_media_id)
        return self.tv_series_external_ids_file(tmdb_media_id)

    # TODO: Validate
    def imdb_title_file(self, imdb_id: str) -> IMDbTitle:
        return self._cached_file(IMDbTitle, imdb_id)

    # TODO: Validate
    def _upsert_imdb_score(self, tmdb_title: Title) -> None:
        tmdb_title.imdb_score = None
        tmdb_title.imdb_popularity = None

        external_ids_file = self.external_ids_file(tmdb_title.key)
        external_ids_file.download_if_outdated()
        tmdb_title.set_update_at(external_ids_file.record_update_at)
        imdb_id = external_ids_file.imdb_id()
        if imdb_id is None:
            return

        imdb_title_file = self.imdb_title_file(imdb_id)
        imdb_title_file.download_if_outdated()
        tmdb_title.set_update_at(imdb_title_file.record_update_at)
        if imdb_title_file.record_content is None:
            return

        imdb_title = imdb_title_file.parsed().data.title
        meter_ranking = imdb_title.meter_ranking
        tmdb_title.imdb_score = imdb_title.ratings_summary.aggregate_rating
        tmdb_title.imdb_popularity = (
            meter_ranking.current_rank if meter_ranking else None
        )
