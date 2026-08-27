# TODO: Validate
"""Store what TMDB holds the way every other plugin stores what its website holds.

TMDB is a plugin like any other: it has a `Source`, and it writes its own `Show`,
`Season` and `Episode` rows through the same upsert every website's plugin uses. What is
different is what those rows are. TMDB is the record of what a title is rather than a
website carrying it, so its rows are the canonical rows themselves and point at nothing,
which is what every other plugin's non-canonical row points at instead. Nothing can be
watched on TMDB, so its records are left out wherever media is being chosen to play.
"""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.canonical_media.service import (
    canonical_episode_by_key,
    canonical_season_by_key,
    canonical_show_by_key,
)
from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.TMDB.constants import media_url
from plugins.TMDB.helpers import (
    HelperMixin,
    SeasonSource,
    air_datetime,
    backdrop_image_url,
    duration_seconds,
    poster_image_url,
    release_year,
    still_image_url,
)
from plugins.TMDB.keys import (
    episode_key,
    parse_show_key,
    season_key,
)


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Reads TMDB into records of TMDB's own."""

    # TODO: Validate
    @override
    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=self._existing_data_timestamp_or_now(source),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

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
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            show = self._upsert_movie_show(source, show_key, tmdb_id, force=force)
        else:
            show = self._upsert_series_show(source, show_key, tmdb_id, force=force)

        return show

    # TODO: Validate
    def _stored_title(self, source: Source, show_key: str) -> Show:
        """Return the row standing for this title, whatever wrote it.

        Asked of the canonical service rather than looked up here, because that
        is what everything else naming a title before it is imported asks too -
        the linker pointing a listing at one - and both have to come back with
        the same row. It remembers what it answered with, so a lookup that went
        around it would be answered again with a row of its own.
        """
        return canonical_show_by_key(self.session, show_key, source)

    # TODO: Validate
    def _stored_season(self, show: Show, season_key: str) -> Season:
        """Return the row standing for this season, whatever wrote it."""
        return canonical_season_by_key(self.session, season_key, show)

    # TODO: Validate
    def _stored_episode(self, season: Season, episode_key: str) -> Episode:
        """Return the row standing for this episode, whatever wrote it."""
        return canonical_episode_by_key(
            self.session,
            episode_key,
            season,
            self.plugin.key,
        )

    # TODO: Validate
    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> Show:
        show = self._stored_title(source, show_key)
        if self._show_is_outdated(show, force=force):
            series = self.show_detail_file(tmdb_id).parsed()
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=series.name,
                description=series.overview,
                url=media_url(MediaType.tv, tmdb_id),
                image_url=backdrop_image_url(series.backdrop_path)
                or poster_image_url(series.poster_path),
                year=release_year(series.first_air_date),
                media_type="TV Show",
                data_timestamp=data_timestamp,
                update_at=data_timestamp + timedelta(days=7),
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_series_seasons(show, show_key, tmdb_id, force=force)
        self._soft_delete_missing(show_key)
        return show

    # TODO: Validate
    def _upsert_series_seasons(
        self,
        show: Show,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> None:
        # Whichever order the title is read in, seasons and episodes come back
        # the same shape, so nothing below asks which it was.
        for source in self.series_seasons(show_key):
            season = self._stored_season(show, source.key)
            if self._season_is_outdated(season, show_key, force=force):
                data_timestamp = self.season_data_timestamp(source.key, show_key)
                new_season = Season(
                    key=source.key,
                    name=source.name,
                    season_number=source.season_number,
                    sort_order=source.season_number,
                    url=media_url(MediaType.tv, tmdb_id),
                    image_url=poster_image_url(source.poster_path),
                    data_timestamp=data_timestamp,
                    update_at=None,
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show_key,
                )
            self._upsert_series_episodes(
                season,
                source,
                show_key,
                tmdb_id,
                force=force,
            )

    # TODO: Validate
    def _upsert_series_episodes(
        self,
        season: Season,
        source: SeasonSource,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> None:
        season_key = source.key
        for sort_order, episode_source in enumerate(source.episodes):
            key = episode_key(MediaType.tv, episode_source.id)
            episode = self._stored_episode(season, key)
            if not self._episode_is_outdated(
                episode,
                season_key,
                show_key,
                force=force,
            ):
                continue
            data_timestamp = self.episode_data_timestamp(key, season_key, show_key)
            new_episode = Episode(
                key=key,
                name=episode_source.name,
                description=episode_source.overview,
                url=media_url(MediaType.tv, tmdb_id),
                image_url=still_image_url(episode_source.still_path),
                duration=duration_seconds(episode_source.runtime),
                air_date=air_datetime(episode_source.air_date),
                episode_number=episode_source.number,
                sort_order=sort_order,
                data_timestamp=data_timestamp,
                update_at=None,
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)

    # TODO: Validate
    def _upsert_movie_show(
        self,
        source: Source,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> Show:
        movie = self.movie_detail_file(tmdb_id).parsed()
        show = self._stored_title(source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=movie.title,
                description=movie.overview,
                url=media_url(MediaType.movie, tmdb_id),
                image_url=backdrop_image_url(movie.backdrop_path)
                or poster_image_url(movie.poster_path),
                year=release_year(movie.release_date),
                media_type="Movie",
                data_timestamp=data_timestamp,
                update_at=data_timestamp + timedelta(days=7),
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_movie_season(show, show_key, tmdb_id, force=force)
        return show

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> None:
        movie = self.movie_detail_file(tmdb_id).parsed()
        key = season_key(MediaType.movie, tmdb_id)
        season = self._stored_season(show, key)
        if self._season_is_outdated(season, show_key, force=force):
            data_timestamp = self.season_data_timestamp(key, show_key)
            new_season = Season(
                key=key,
                name=movie.title,
                season_number=0,
                sort_order=0,
                url=media_url(MediaType.movie, tmdb_id),
                image_url=poster_image_url(movie.poster_path),
                data_timestamp=data_timestamp,
                update_at=None,
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show_key)

        self._upsert_movie_episode(season, key, show_key, tmdb_id, force=force)

    # TODO: Validate
    def _upsert_movie_episode(
        self,
        season: Season,
        season_key: str,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> None:
        movie = self.movie_detail_file(tmdb_id).parsed()
        key = episode_key(MediaType.movie, tmdb_id)
        episode = self._stored_episode(season, key)
        if not self._episode_is_outdated(episode, season_key, show_key, force=force):
            return
        data_timestamp = self.episode_data_timestamp(key, season_key, show_key)
        new_episode = Episode(
            key=key,
            name=movie.title,
            description=movie.overview,
            url=media_url(MediaType.movie, tmdb_id),
            image_url=backdrop_image_url(movie.backdrop_path),
            duration=duration_seconds(movie.runtime),
            air_date=air_datetime(movie.release_date),
            episode_number=0,
            sort_order=0,
            data_timestamp=data_timestamp,
            update_at=None,
            season_id=season.id,
        )
        self._upsert_episode_object(new_episode, season, episode, show_key)
