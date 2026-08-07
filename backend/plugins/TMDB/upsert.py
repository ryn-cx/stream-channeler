# TODO: Validate
from __future__ import annotations

from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.TMDB.files import (
    air_datetime,
    backdrop_image_url,
    duration_seconds,
    poster_image_url,
    still_image_url,
    title_page_url,
)
from plugins.TMDB.helpers import HelperMixin
from plugins.TMDB.keys import (
    MOVIE_EPISODE_NUMBER,
    MOVIE_SEASON_NUMBER,
    MediaType,
    episode_key,
    parse_show_key,
    season_key,
    show_key,
)


class UpsertMixin(HelperMixin, register=False):
    def import_title(self, media_type: MediaType, tmdb_id: int) -> Show | None:
        """Store a title and everything under it as this plugin's own media.

        Other plugins fall back to these records for whatever their own website
        does not carry, so a title is imported as soon as one of them resolves
        it rather than only when a `User` asks for it.

        Returns None when TMDB has no files for the title, which leaves the
        plugin's own media as the only thing there is to serve.
        """
        key = show_key(media_type, tmdb_id)
        detail_file = self._show_files(key)[0]
        detail_file.download_if_outdated()
        if detail_file.is_outdated():
            return None
        return self._import_show(key)

    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        media_type = parse_show_key(show_key).media_type
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            show = self._new_show(source, show_key).upsert_and_set_update_at(
                source,
                show,
                self._show_files(show_key),
            )

        if media_type == "movie":
            self._upsert_movie_season(show, show_key, force=force)
        else:
            for key in self._season_keys_from_file(show_key):
                self._upsert_season(show, key, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _new_show(self, source: Source, show_key: str) -> Show:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == "movie":
            movie = self.movie_detail_file(tmdb_id).parsed()
            name = movie.title
            description = movie.overview
            image_url = backdrop_image_url(movie.backdrop_path) or poster_image_url(
                movie.poster_path,
            )
        else:
            series = self.show_detail_file(tmdb_id).parsed()
            name = series.name
            description = series.overview
            image_url = backdrop_image_url(series.backdrop_path) or poster_image_url(
                series.poster_path,
            )

        return Show(
            key=show_key,
            name=name,
            description=description,
            media_type="Movie" if media_type == "movie" else "TV Show",
            url=title_page_url(media_type, tmdb_id),
            image_url=image_url,
            tmdb_id=tmdb_id,
            show_identifier=f"TMDB {media_type} {tmdb_id}",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        )

    def _upsert_season(
        self,
        show: Show,
        season_key: str,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        media_type, tmdb_id = parse_show_key(show_key)
        season_number = int(season_key.rsplit("/", 1)[1])
        detail = self.season_detail_file(tmdb_id, season_number).parsed()

        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show_key, force=force):
            season = Season(
                key=season_key,
                name=detail.name,
                sort_order=season_number,
                season_number=season_number,
                url=title_page_url(media_type, tmdb_id),
                image_url=poster_image_url(detail.poster_path),
                tmdb_id=detail.id,
                season_identifier=f"TMDB tv {detail.id}",
                data_timestamp=self.season_data_timestamp(season_key, show_key),
                show_id=show.id,
            ).upsert_and_set_update_at(
                show,
                season,
                self._season_files(season_key, show_key),
            )

        for sort_order, episode in enumerate(detail.episodes):
            key = episode_key(
                media_type,
                tmdb_id,
                season_number,
                episode.episode_number,
            )
            existing = Episode.get_from_memory(self.session, season, key)
            if not self._episode_is_outdated(
                existing,
                season_key,
                show_key,
                force=force,
            ):
                continue

            air = air_datetime(episode.air_date)
            Episode(
                key=key,
                name=episode.name,
                description=episode.overview,
                url=title_page_url(media_type, tmdb_id),
                image_url=still_image_url(episode.still_path),
                duration=duration_seconds(episode.runtime),
                release_date=air,
                air_date=air,
                sort_order=sort_order,
                episode_number=episode.episode_number,
                episode_identifier=f"TMDB tv {episode.id}",
                tmdb_id=episode.id,
                data_timestamp=self.episode_data_timestamp(key, season_key, show_key),
                season_id=season.id,
            ).upsert_and_set_update_at(
                season,
                existing,
                self._episode_files(key, season_key, show_key),
            )

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        """Store a movie as a single season holding the movie as its only episode."""
        media_type, tmdb_id = parse_show_key(show_key)
        movie = self.movie_detail_file(tmdb_id).parsed()
        key = season_key(media_type, tmdb_id, MOVIE_SEASON_NUMBER)

        season = Season.get_from_memory(self.session, show, key)
        if self._season_is_outdated(season, show_key, force=force):
            season = Season(
                key=key,
                name=movie.title,
                sort_order=MOVIE_SEASON_NUMBER,
                season_number=MOVIE_SEASON_NUMBER,
                url=title_page_url(media_type, tmdb_id),
                image_url=poster_image_url(movie.poster_path),
                tmdb_id=movie.id,
                season_identifier=f"TMDB movie {movie.id}",
                data_timestamp=self.season_data_timestamp(key, show_key),
                show_id=show.id,
            ).upsert_and_set_update_at(show, season, self._season_files(key, show_key))

        movie_key = episode_key(
            media_type,
            tmdb_id,
            MOVIE_SEASON_NUMBER,
            MOVIE_EPISODE_NUMBER,
        )
        episode = Episode.get_from_memory(self.session, season, movie_key)
        if not self._episode_is_outdated(episode, key, show_key, force=force):
            return

        release = air_datetime(movie.release_date)
        Episode(
            key=movie_key,
            name=movie.title,
            description=movie.overview,
            url=title_page_url(media_type, tmdb_id),
            image_url=backdrop_image_url(movie.backdrop_path),
            duration=duration_seconds(movie.runtime),
            release_date=release,
            air_date=release,
            sort_order=MOVIE_EPISODE_NUMBER,
            episode_number=MOVIE_EPISODE_NUMBER,
            episode_identifier=f"TMDB movie {movie.id}",
            tmdb_id=movie.id,
            data_timestamp=self.episode_data_timestamp(movie_key, key, show_key),
            season_id=season.id,
        ).upsert_and_set_update_at(
            season,
            episode,
            self._episode_files(movie_key, key, show_key),
        )
