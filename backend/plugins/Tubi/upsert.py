# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Tubi.helpers import HelperMixin

_SERIES_UPDATE_INTERVAL = timedelta(days=7)


_MOVIE_UPDATE_INTERVAL = timedelta(days=30)


class UpsertMixin(HelperMixin, register=False):
    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if self._is_movie(show_key):
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
            content = self._content(show_key)
            show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="TV Show",
                url=self._series_url(show_key),
                image_url=self._first_image(content.backgrounds),
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
        for sort_order, season_content in enumerate(self._seasons(show.key)):
            season_key = self._season_key(show.key, season_content.id)
            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    name=season_content.title,
                    season_number=int(season_content.id),
                    sort_order=sort_order,
                    url=self._series_url(show.key),
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
                season_content.id,
                force=force,
            )

    def _upsert_series_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_content in enumerate(
            self._season_episodes(show_key, season_id),
        ):
            episode_key = episode_content.id
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
                name=self._episode_name(episode_content.title),
                description=episode_content.description,
                episode_number=int(episode_content.episode_number),
                url=self._episode_url(episode_key),
                image_url=self._first_image(episode_content.thumbnails),
                duration=episode_content.duration,
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
        content = self._content(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
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
            content = self._content(show_key)
            episode = Episode(
                key=show_key,
                name=content.title,
                description=content.description,
                episode_number=0,
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
                duration=content.duration,
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
