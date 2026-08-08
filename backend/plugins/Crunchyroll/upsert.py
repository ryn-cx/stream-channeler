# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Protocol, cast, override

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import (
    CATEGORY_NAMES,
    MUSIC_CATEGORIES,
    MUSIC_SOURCE_KEY,
    MUSIC_SOURCE_NAME,
    VIDEO_SOURCE_KEY,
    VIDEO_SOURCE_NAME,
    MusicCategory,
    is_artist_show_key,
    music_episode_key,
    music_season_key,
    parse_artist_show_key,
)
from plugins.TMDB.mixin import highest_episode_number

# Crunchyroll adds music far more slowly than it airs episodes, and the music
# catalogue offers no cutoff parameter so every check downloads all of it. The
# music `Source` is scheduled a month out, which is what makes the check monthly.
MUSIC_UPDATE_INTERVAL = timedelta(days=30)


class _SizedImage(Protocol):
    """One of the sizes Crunchyroll offers an image in."""

    source: str
    width: int


class _Release(Protocol):
    """An entry in one of an artist's listings.

    A music video listing and a concert listing are separate models with no
    shared base beyond pydantic's, so the one field read off both is named here.
    """

    id: str


class UpsertMixin(HelperMixin, register=False):
    """Mixin containing all upsert functions."""

    def _upsert_video_source(self) -> Source:
        # If this is the first time the source is upserted an initial browse file needs
        # to be downloaded.
        if not (latest_browse_file := self.find_newest_browse_file()):
            latest_browse_file = self.browse_series_file(tz_datetime.now())
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, VIDEO_SOURCE_KEY)
        return Source(
            key=VIDEO_SOURCE_KEY,
            name=VIDEO_SOURCE_NAME,
            favicon_url=self.FAVICON_URL,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + timedelta(days=1),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())

    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        """Upsert a `Show`, from whichever catalogue its key belongs to."""
        if is_artist_show_key(show_key):
            return self._upsert_music_show(source, show_key, force=force)
        return self._upsert_video_show(source, show_key, force=force)

    def _upsert_video_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        tmdb_media_type = self.tmdb_media_type(show_key)

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series_data = self._series_datum(show_key)
            new_show = Show(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if self._is_movie(show_key) else "Series",
                url=self._show_url(series_data.id),
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                tmdb_media_type,
            )

        self._upsert_video_seasons(show, tmdb_media_type, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_video_seasons(
        self,
        show: Show,
        tmdb_media_type: MediaType,
        *,
        force: bool = False,
    ) -> None:
        seasons_file = self.seasons_file(show.key)
        for index, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.session, show, season_data.id)
            if self._season_is_outdated(season, force=force):
                new_season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=index,
                    season_identifier=self._fallback_season_identifier(season_data.id),
                    data_timestamp=self.season_data_timestamp(
                        season_data.id,
                        show.key,
                    ),
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    new_season,
                    show,
                    season,
                    show.key,
                    tmdb_media_type,
                )

            self._upsert_video_episodes(
                season,
                show.key,
                tmdb_media_type,
                force=force,
            )

    def _upsert_video_episodes(
        self,
        season: Season,
        show_key: str,
        tmdb_media_type: MediaType,
        *,
        force: bool = False,
    ) -> None:
        episodes_data = self.season_episodes_file(season.key).parsed()
        last_number = highest_episode_number(
            episode_data.episode_number for episode_data in episodes_data.data
        )
        for index, episode_data in enumerate(episodes_data.data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(episode, force=force):
                continue
            new_episode = Episode(
                key=episode_data.id,
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self._episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                duration=episode_data.duration_ms // 1000,
                sort_order=index,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                episode_identifier=f"{self.plugin_key()} {episode_data.id}",
                data_timestamp=self.episode_data_timestamp(
                    episode_data.id,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                new_episode,
                season,
                episode,
                show_key,
                tmdb_media_type,
                last_number,
            )

    def _upsert_music_source(self) -> Source:
        # If this is the first time the source is upserted an initial browse file
        # needs to be downloaded.
        if not (latest_browse_file := self.find_newest_music_browse_file()):
            latest_browse_file = self.browse_music_file(tz_datetime.now())
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, MUSIC_SOURCE_KEY)
        return Source(
            key=MUSIC_SOURCE_KEY,
            name=MUSIC_SOURCE_NAME,
            favicon_url=self.FAVICON_URL,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + MUSIC_UPDATE_INTERVAL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._music_source_files())

    def _upsert_music_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        artist_id = parse_artist_show_key(show_key)

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            artist_data = self.artist_file(artist_id).parsed().data[0]
            show = Show(
                key=show_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self._show_url(show_key),
                image_url=self._largest_image(artist_data.images.poster_wide),
                show_identifier=f"{self.plugin_key()} {show_key}",
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            ).upsert_and_set_update_at(source, show, self._show_files(show_key))

        self._upsert_music_seasons(show, artist_id, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_music_seasons(
        self,
        show: Show,
        artist_id: str,
        *,
        force: bool = False,
    ) -> None:
        # An artist always has both categories, even while one is empty, so a
        # first release into it is a new episode rather than a new season.
        for sort_order, category in enumerate(MUSIC_CATEGORIES):
            season_key = music_season_key(artist_id, category)

            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                season = Season(
                    key=season_key,
                    name=CATEGORY_NAMES[category],
                    sort_order=sort_order,
                    url=self._show_url(show.key),
                    season_identifier=f"{self.plugin_key()} {season_key}",
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                ).upsert_and_set_update_at(
                    show,
                    season,
                    self._season_files(season_key, show.key),
                )

            self._upsert_music_episodes(
                season,
                show.key,
                artist_id,
                category,
                force=force,
            )

    def _upsert_music_episodes(
        self,
        season: Season,
        show_key: str,
        artist_id: str,
        category: MusicCategory,
        *,
        force: bool = False,
    ) -> None:
        listing = cast(
            "Sequence[_Release]",
            self.artist_category_file(artist_id, category).parsed().data,
        )
        # Crunchyroll lists an artist's releases newest first, so the order is
        # reversed to number them the way they were released.
        for sort_order, datum in enumerate(reversed(listing)):
            episode_key = music_episode_key(category, datum.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            details = self.music_file(episode_key).parsed().data[0]
            Episode(
                key=episode_key,
                name=details.title,
                description=details.description,
                url=self._episode_url(episode_key),
                image_url=self._largest_image(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                release_date=details.availability.start_date,
                air_date=details.original_release,
                episode_identifier=f"{self.plugin_key()} {datum.id}",
                data_timestamp=self.episode_data_timestamp(
                    episode_key,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            ).upsert_and_set_update_at(
                season,
                episode,
                self._episode_files(episode_key, season.key, show_key),
            )

    @staticmethod
    def _largest_image(images: Sequence[_SizedImage]) -> str | None:
        """Return the source of the widest size Crunchyroll offers an image in."""
        if not images:
            return None
        return max(images, key=lambda image: image.width).source
