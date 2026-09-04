# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.Hulu.upsert import MovieUpsertMixin, SeriesUpsertMixin, UpsertMixin
from plugins.utils.base_plugin_v2.importer import BasePluginWorker

if TYPE_CHECKING:
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class HuluMedia(BasePluginWorker, ABC):
    pass


# TODO: Validate
class HuluSeries(SeriesUpsertMixin, HuluMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> tuple[str, TMDBMediaType | None, int | None]:
        parsed_series = self.series_file(show_key).parsed()
        return (
            parsed_series.name,
            TMDBMediaType.tv,
            parsed_series.details.entity.premiere_date.year,
        )


# TODO: Validate
class HuluMovie(MovieUpsertMixin, HuluMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> tuple[str, TMDBMediaType | None, int | None]:
        parsed_movie = self.movie_file(show_key).parsed()
        return (
            parsed_movie.name,
            TMDBMediaType.movie,
            parsed_movie.details.entity.premiere_date.year,
        )


# TODO: Validate
class MediaMixin(UpsertMixin):
    # TODO: Validate
    def _media_plugin(self, show: Show) -> HuluMedia:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if show.media_type == "Movie":
            return HuluMovie(self)
        return HuluSeries(self)

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        stored_show = self._preload_show(show_key, source_key=source.key).one()
        return self._media_plugin(stored_show).upsert_show(
            source,
            show_key,
            canonical_show,
            force=force,
        )
