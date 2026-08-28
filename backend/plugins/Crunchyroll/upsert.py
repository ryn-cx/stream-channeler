# TODO: Validate
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Literal, override

from chirashi.artist.models import PosterWideItem as ArtistPosterWideItem
from chirashi.artist_concerts.models import Datum as ConcertListingDatum
from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum
from chirashi.concert.models import ThumbnailItem as ConcertThumbnailItem
from chirashi.music_video.models import ThumbnailItem as MusicVideoThumbnailItem
from chirashi.season_episodes.models import Images as EpisodeImages
from chirashi.series.models import Images as SeriesImages

from app.episodes.models import Episode
from app.files.models import File
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.constants import (
    MusicCategory,
    show_is_a_series,
    show_is_an_artist,
)
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries
from plugins.Crunchyroll.utils import HelperMixin
from plugins.utils.base_plugin.files import INITIAL_FILE_IDENTIFIER


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Mixin containing all upsert functions."""

    # TODO: Validate
    @override
    def _upsert_source(
        self,
        source_key: str,
        latest_browse_file: BrowseSeries | BrowseMusic | None,
        browse_file: Callable[
            [datetime | File | Literal["Initial"]],
            BrowseSeries | BrowseMusic,
        ],
        update_interval: timedelta,
    ) -> Source:
        # If this is the first time the source is upserted an initial browse file needs
        # to be downloaded.
        if not latest_browse_file:
            latest_browse_file = browse_file(INITIAL_FILE_IDENTIFIER)
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        # TODO: Consider implementing something like _upsert_show_object but for
        # sources.
        return Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            data_timestamp=data_timestamp,
            update_at=data_timestamp + update_interval,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, existing_source, [latest_browse_file])

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
        if show_is_an_artist(show_key):
            show = self._upsert_music_show(source, show_key, force=force)
        elif show_is_a_series(show_key):
            show = self._upsert_video_show(source, show_key, force=force)
        else:
            msg = f"Show key {show_key} is invalid and not supported."
            raise ValueError(msg)

        add_canonical_show_and_link_episodes(self.session, show, canonical_show)
        return show

    # TODO: Validate
    def _upsert_video_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series_data = self._series_datum(show_key)
            new_show = Show(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if self._is_movie(show_key) else "Series",
                url=self._series_url(series_data.id),
                image_url=self._show_image(series_data.images),
                year=series_data.series_launch_year,
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_anime_seasons(show, force=force)
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
            new_show = Show(
                key=show_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self._artist_url(show_key),
                image_url=self._largest_image(artist_data.images.poster_wide),
                data_timestamp=self.show_data_timestamp(show_key),
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_music_seasons(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_anime_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        seasons_file = self.seasons_file(show.key)
        for index, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.session, show, season_data.id)
            if self._season_is_outdated(season, show.key, force=force):
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
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show.key,
                )

            self._upsert_video_episodes(
                season,
                show.key,
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
                    name={
                        MusicCategory.CONCERT: "Concerts",
                        MusicCategory.MUSIC_VIDEO: "Music Videos",
                    }[category],
                    url=self._artist_url(show.key),
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
        *,
        force: bool = False,
    ) -> None:
        episodes_data = self.season_episodes_file(season.key).parsed()
        for index, episode_data in enumerate(episodes_data.data):
            episode = Episode.get_from_memory(
                self.session,
                season,
                episode_data.id,
            )
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue
            new_episode = Episode(
                key=episode_data.id,
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self._episode_url(episode_data.id),
                description=episode_data.description,
                image_url=self._episode_thumbnail(episode_data.images),
                duration=episode_data.duration_ms // 1000,
                sort_order=index,
                air_date=episode_data.episode_air_date,
                data_timestamp=self.episode_data_timestamp(
                    episode_data.id,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(
                new_episode,
                season,
                episode,
                show_key,
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
        listing: Sequence[ConcertListingDatum | MusicVideoListingDatum] = (
            self.artist_concerts_or_artist_music_videos_file(
                artist_id,
                category,
            )
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

            details = (
                self.concert_or_music_video_file(
                    episode_key,
                )
                .parsed()
                .data[0]
            )
            Episode(
                key=episode_key,
                name=details.title,
                description=details.description,
                url=self._episode_url(episode_key),
                image_url=self._largest_image(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                air_date=details.original_release,
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
    def _show_image(images: SeriesImages) -> str | None:
        """Return the widest poster a listing carries, where it carries one.

        The wide one first because that is the shape the artwork is shown in,
        the tall one being what is left for a listing Crunchyroll has only a
        portrait poster of.
        """
        wide = images.poster_wide
        if wide and wide[0]:
            return max(wide[0], key=lambda image: image.width).source
        tall = images.poster_tall
        if tall and tall[0]:
            return max(tall[0], key=lambda image: image.width).source
        return None

    # TODO: Validate
    @staticmethod
    def _episode_thumbnail(images: EpisodeImages) -> str | None:
        """Return the largest thumbnail an episode has, where it has one at all.

        An episode Crunchyroll has no thumbnail for carries no sizes to pick
        from, and older ones carry none of the field at all.
        """
        thumbnails = images.thumbnail
        if not thumbnails or not thumbnails[0]:
            return None
        return thumbnails[0][-1].source

    # TODO: Validate
    @staticmethod
    def _largest_image(
        images: Sequence[
            ArtistPosterWideItem | ConcertThumbnailItem | MusicVideoThumbnailItem
        ],
    ) -> str | None:
        """Return the source of the widest size Crunchyroll offers an image in."""
        if not images:
            return None
        return max(images, key=lambda image: image.width).source
