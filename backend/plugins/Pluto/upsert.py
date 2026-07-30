# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Pluto.helpers import HelperMixin

# The website serves every on-demand page under a locale segment.


_SERIES_UPDATE_INTERVAL = timedelta(days=7)


_MOVIE_UPDATE_INTERVAL = timedelta(days=30)


_MILLISECONDS_PER_SECOND = 1000


class UpsertMixin(HelperMixin, register=False):
    @override
    def _upsert_show(
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

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            series = self._series(show_key)
            show = Show(
                key=show_key,
                name=series.name,
                description=series.description,
                media_type="TV Show",
                url=self._series_url(show_key),
                image_url=series.featured_image.path,
                data_timestamp=show_check.data_timestamp,
                update_at=show_check.data_timestamp + _SERIES_UPDATE_INTERVAL,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                show,
                source,
                show_check.record,
                show_key,
                "tv",
            )
        else:
            show = show_check.record

        self._upsert_series_seasons(show, force=force)

        return show

    def _upsert_series_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, series_season in enumerate(self._seasons(show.key)):
            season_key = self._season_key(show.key, series_season.number)
            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    season_number=series_season.number,
                    sort_order=sort_order,
                    url=self._season_url(show.key, series_season.number),
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    season,
                    show,
                    season_check.record,
                    show.key,
                    "tv",
                )
            else:
                season = season_check.record

            self._upsert_series_episodes(
                season,
                show.key,
                series_season.number,
                force=force,
            )

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
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            episode = Episode(
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
                episode_identifier=f"{self.plugin_key()} {episode_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                episode,
                season,
                episode_check.record,
                show_key,
                "tv",
            )

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        item = self._item(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=item.name,
                description=item.description,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=item.featured_image.path,
                data_timestamp=show_check.data_timestamp,
                update_at=show_check.data_timestamp + _MOVIE_UPDATE_INTERVAL,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                show,
                source,
                show_check.record,
                show_key,
                "movie",
            )
        else:
            show = show_check.record

        self._upsert_movie_season(show, force=force)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._movie_season_key(show.key)
        if season_check := self._season_check(show, season_key, show.key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._movie_url(show.key),
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                season,
                show,
                season_check.record,
                show.key,
                "movie",
            )
        else:
            season = season_check.record

        self._upsert_movie_episode(season, show.key, force=force)

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        if episode_check := self._episode_check(
            show_key,
            season,
            show_key,
            force=force,
        ):
            item = self._item(show_key)
            episode = Episode(
                key=show_key,
                name=item.name,
                description=item.description,
                episode_number=0,
                url=self._movie_url(show_key),
                image_url=item.featured_image.path,
                duration=item.original_content_duration // _MILLISECONDS_PER_SECOND,
                sort_order=0,
                episode_identifier=f"{self.plugin_key()} {show_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                episode,
                season,
                episode_check.record,
                show_key,
                "movie",
            )
