# TODO: Validate
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import override

from chirashi.artist import models as artist_models
from chirashi.artist_concerts import models as artist_concerts_models
from chirashi.artist_music_videos import models as artist_music_videos_models
from chirashi.concert import models as concert_models
from chirashi.music_video import models as music_video_models

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import (
    MUSIC_CATEGORY_TO_NAME,
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    MusicCategory,
    is_anime_show_key,
    is_music_show_key,
)
from plugins.TMDB.mixin import highest_episode_number


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Mixin containing all upsert functions."""

    # TODO: Validate
    def _upsert_anime_source(self) -> Source:
        return self._upsert_source(
            VIDEO_SOURCE,
            self.find_newest_browse_file(),
            BrowseSeries,
            timedelta(days=1),  # Check daily for new videos.
        )

    # TODO: Validate
    def _upsert_music_source(self) -> Source:
        return self._upsert_source(
            MUSIC_SOURCE,
            self.find_newest_music_browse_file(),
            BrowseMusic,
            timedelta(days=7),  # Check weekly for new music.
        )

    # TODO: Validate
    @override
    def _upsert_source(
        self,
        source_key: str,
        latest_browse_file: BrowseSeries | BrowseMusic | None,
        initial_file_type: Callable[..., BrowseSeries | BrowseMusic],
        update_interval: timedelta,
    ) -> Source:
        # If this is the first time the source is upserted an initial browse file needs
        # to be downloaded.
        if not latest_browse_file:
            latest_browse_file = self._initial_file(initial_file_type)
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=source_key,
            favicon_url=self.FAVICON_URL,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + update_interval,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, [latest_browse_file])

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if is_music_show_key(show_key):
            return self._upsert_music_show(source, show_key, force=force)

        if is_anime_show_key(show_key):
            return self._upsert_anime_show(source, show_key, force=force)

        msg = f"Show key {show_key} is neither an artist nor a series"
        raise ValueError(msg)

    # TODO: Validate
    def _upsert_anime_show(
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
                url=self._series_url(series_data.id),
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

        self._upsert_anime_seasons(show, tmdb_media_type, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)

        return show

    # TODO: Validate
    def _upsert_music_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            artist_data = self.artist_file(show_key).parsed().data[0]
            show = Show(
                key=show_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self._artist_url(show_key),
                image_url=self._largest_image(artist_data.images.poster_wide),
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            ).upsert_and_set_update_at(source, show, self._show_files(show_key))

        self._upsert_music_seasons(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_anime_seasons(
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

    # TODO: Validate
    def _upsert_music_seasons(
        self,
        show: Show,
        artist_id: str,
        *,
        force: bool = False,
    ) -> None:

        for category in MusicCategory:
            season = Season.get_from_memory(self.session, show, category)
            if self._season_is_outdated(season, show.key, force=force):
                season = Season(
                    key=category,
                    name=MUSIC_CATEGORY_TO_NAME[category],
                    url=self._artist_url(show.key),
                    season_identifier=self._fallback_season_identifier(category),
                    data_timestamp=self.season_data_timestamp(category, show.key),
                    show_id=show.id,
                ).upsert_and_set_update_at(
                    show,
                    season,
                    self._season_files(category, show.key),
                )

            self._upsert_music_episodes(
                season,
                show.key,
                artist_id,
                category,
                force=force,
            )

    # TODO: Validate
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

    # TODO: Validate
    def _upsert_music_episodes(
        self,
        season: Season,
        show_key: str,
        artist_id: str,
        category: MusicCategory,
        *,
        force: bool = False,
    ) -> None:
        listing: Sequence[
            artist_concerts_models.Datum | artist_music_videos_models.Datum
        ] = (
            self.artist_concerts_or_artist_music_videos_file(artist_id, category)
            .parsed()
            .data
        )
        # Crunchyroll lists an artist's releases newest first, so the order is
        # reversed to number them the way they were released.
        for sort_order, datum in enumerate(reversed(listing)):
            episode_key = datum.id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            details = self.concert_or_music_video_file(episode_key).parsed().data[0]
            Episode(
                key=episode_key,
                name=details.title,
                description=details.description,
                url=self._episode_url(episode_key),
                image_url=self._largest_image(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                release_date=details.availability.start_date,
                air_date=details.original_release,
                episode_identifier=self._fallback_episode_identifier(datum.id),
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

    # TODO: Validate
    @staticmethod
    def _largest_image(
        images: Sequence[
            artist_models.PosterWideItem
            | concert_models.ThumbnailItem
            | music_video_models.ThumbnailItem
        ],
    ) -> str | None:
        """Return the source of the widest size Crunchyroll offers an image in."""
        if not images:
            return None
        return max(images, key=lambda image: image.width).source
