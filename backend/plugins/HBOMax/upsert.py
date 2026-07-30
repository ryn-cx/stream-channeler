# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from minbo.movies.models import Idref14 as MovieContent

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.HBOMax.helpers import HelperMixin


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
        self._set_weekly_updates_from_episodes(show, update_show=False)
        return show

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            content = self._show_content(show_key)
            show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=content.image_url_link,
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=30),
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

        self._upsert_tv_seasons(show, force=force)

        return show

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        content = self._movie_content(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=content.image_url_link,
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=30),
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

    def _upsert_tv_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(show.key)):
            season_key = self._season_key(show.key, season_number)
            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                entry = self._season_entry(show.key, season_number)
                season = Season(
                    key=season_key,
                    name=entry.title.full,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key),
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

            self._upsert_tv_episodes(season, show.key, season_number, force=force)

    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        content = self._movie_content(show.key)
        season_key = self._season_key(show.key, 0)
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

        self._upsert_movie_episode(season, show.key, content, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        episodes = self._season_episodes(show_key, season_number)
        for sort_order, item in enumerate(episodes):
            episode_key = self._episode_key(season.key, item.episode_number)
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
                name=str(item.title.full),
                episode_number=item.episode_number,
                url=item.episode_url,
                description=item.summary.full,
                image_url=item.images.default,
                release_date=item.offering_dates.start_date,
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

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        content: MovieContent,
        *,
        force: bool = False,
    ) -> None:
        if episode_check := self._episode_check(
            show_key,
            season,
            show_key,
            force=force,
        ):
            episode = Episode(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                url=self._movie_url(show_key),
                image_url=content.image_url_link,
                episode_number=0,
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
