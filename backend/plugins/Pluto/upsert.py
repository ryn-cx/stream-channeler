# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Pluto.helpers import HelperMixin

# The website serves every on-demand page under a locale segment.


_SERIES_UPDATE_INTERVAL = timedelta(days=7)


_MOVIE_UPDATE_INTERVAL = timedelta(days=30)


_MILLISECONDS_PER_SECOND = 1000


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if self._is_movie():
            show = self._upsert_movie(source, show_key, force=force)
        else:
            show = self._upsert_series_show(source, show_key, force=force)
        self._soft_delete_missing(show_key)
        return show

    # TODO: Validate
    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series = self._series(show_key)
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=series.name,
                description=series.description,
                media_type="TV Show",
                url=self._series_url(show_key),
                image_url=series.featured_image.path,
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _SERIES_UPDATE_INTERVAL,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                MediaType.tv,
            )

        self._upsert_series_seasons(show, force=force)

        return show

    # TODO: Validate
    def _upsert_series_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, series_season in enumerate(self._seasons(show.key)):
            season_key = self._season_key(show.key, series_season.number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, force=force):
                new_season = Season(
                    key=season_key,
                    season_number=series_season.number,
                    sort_order=sort_order,
                    url=self._season_url(show.key, series_season.number),
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    new_season,
                    show,
                    season,
                    show.key,
                    MediaType.tv,
                )

            self._upsert_series_episodes(
                season,
                show.key,
                series_season.number,
                force=force,
            )

    # TODO: Validate
    def _upsert_series_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, series_episode in enumerate(
            self._season_episodes(show_key, season_number),
        ):
            episode_key = series_episode.field_id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
                key=episode_key,
                name=series_episode.name,
                description=series_episode.description,
                episode_number=series_episode.number,
                url=self._episode_url(show_key, season_number, episode_key),
                image_url=series_episode.poster16_9.path,
                duration=(
                    series_episode.original_content_duration // _MILLISECONDS_PER_SECOND
                ),
                release_date=series_episode.clip.original_release_date,
                sort_order=sort_order,
                data_timestamp=self.episode_data_timestamp(
                    episode_key,
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
                MediaType.tv,
            )

    # TODO: Validate
    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        item = self._item(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=item.name,
                description=item.description,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=item.featured_image.path,
                data_timestamp=data_timestamp,
                update_at=data_timestamp + _MOVIE_UPDATE_INTERVAL,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                MediaType.movie,
            )

        self._upsert_movie_season(show, force=force)

        return show

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._movie_season_key(show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._movie_url(show.key),
                data_timestamp=self.season_data_timestamp(season_key, show.key),
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                new_season,
                show,
                season,
                show.key,
                MediaType.movie,
            )

        self._upsert_movie_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, force=force):
            item = self._item(show_key)
            new_episode = Episode(
                key=show_key,
                name=item.name,
                description=item.description,
                episode_number=0,
                url=self._movie_url(show_key),
                image_url=item.featured_image.path,
                duration=item.original_content_duration // _MILLISECONDS_PER_SECOND,
                sort_order=0,
                data_timestamp=self.episode_data_timestamp(
                    show_key,
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
                MediaType.movie,
            )
