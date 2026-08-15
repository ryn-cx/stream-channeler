# TODO: Validate
"""Store what TMDB holds the way every other plugin stores what its website holds.

TMDB is a plugin like any other: it has a `Source`, and it writes its own `Show`,
`Season` and `Episode` rows through the same upsert every website's plugin uses.
What is different is what those rows are. TMDB is the record of what a title is
rather than a website carrying it, so its rows are the canonical rows themselves
and point at nothing, which is what every other plugin's copy points at instead.
Nothing can be watched on TMDB, so its records are left out wherever media is
being chosen to play.
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
from app.models import Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
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
    episode_key,
    parse_show_key,
    season_key,
)

# How long a record stands for before TMDB is read again.
_REFRESH_INTERVAL = timedelta(days=1)


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Reads TMDB into records of TMDB's own."""

    # TODO: Validate
    @override
    def _upsert_plugin(
        self,
        plugin_user: User,
        existing_plugin: Plugin | None,
    ) -> Plugin:
        return Plugin(
            key=self.plugin_key(),
            name=self.plugin_name(),
            version=self._VERSION,
            visibility=Visibility.private,
            anonymous=False,
            user_id=plugin_user.id,
        ).upsert_and_set_update_at(plugin_user, existing_plugin)

    # TODO: Validate
    @override
    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
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
                url=title_page_url(MediaType.tv, tmdb_id),
                image_url=backdrop_image_url(series.backdrop_path)
                or poster_image_url(series.poster_path),
                media_type="TV Show",
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _REFRESH_INTERVAL,
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
        for key in self._season_keys_from_file(show_key):
            season_number = self.season_number(key, show_key)
            season_file = self.season_detail_file(tmdb_id, season_number)
            # A season the title lists but TMDB has no detail for is stored
            # empty, and an empty file has nothing to read a season out of.
            if not season_file.database_record.content:
                continue
            detail = season_file.parsed()
            season = self._stored_season(show, key)
            if self._season_is_outdated(season, show_key, force=force):
                data_timestamp = self.season_data_timestamp(key, show_key)
                new_season = Season(
                    key=key,
                    name=detail.name,
                    season_number=season_number,
                    sort_order=season_number,
                    url=title_page_url(MediaType.tv, tmdb_id),
                    image_url=poster_image_url(detail.poster_path),
                    data_timestamp=data_timestamp,
                    update_at=data_timestamp + _REFRESH_INTERVAL,
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
                key,
                show_key,
                tmdb_id,
                force=force,
            )

    # TODO: Validate
    def _upsert_series_episodes(
        self,
        season: Season,
        season_key: str,
        show_key: str,
        tmdb_id: int,
        *,
        force: bool = False,
    ) -> None:
        season_number = self.season_number(season_key, show_key)
        season_file = self.season_detail_file(tmdb_id, season_number)
        if not season_file.database_record.content:
            return
        for sort_order, entry in enumerate(season_file.parsed().episodes):
            key = episode_key(MediaType.tv, entry.id)
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
                name=entry.name,
                description=entry.overview,
                url=title_page_url(MediaType.tv, tmdb_id),
                image_url=still_image_url(entry.still_path),
                duration=duration_seconds(entry.runtime),
                air_date=air_datetime(entry.air_date),
                episode_number=entry.episode_number,
                sort_order=sort_order,
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _REFRESH_INTERVAL,
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
                url=title_page_url(MediaType.movie, tmdb_id),
                image_url=backdrop_image_url(movie.backdrop_path)
                or poster_image_url(movie.poster_path),
                media_type="Movie",
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _REFRESH_INTERVAL,
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
                season_number=MOVIE_SEASON_NUMBER,
                sort_order=MOVIE_SEASON_NUMBER,
                url=title_page_url(MediaType.movie, tmdb_id),
                image_url=poster_image_url(movie.poster_path),
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _REFRESH_INTERVAL,
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
            url=title_page_url(MediaType.movie, tmdb_id),
            image_url=backdrop_image_url(movie.backdrop_path),
            duration=duration_seconds(movie.runtime),
            air_date=air_datetime(movie.release_date),
            episode_number=MOVIE_EPISODE_NUMBER,
            sort_order=MOVIE_EPISODE_NUMBER,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + _REFRESH_INTERVAL,
            season_id=season.id,
        )
        self._upsert_episode_object(new_episode, season, episode, show_key)
