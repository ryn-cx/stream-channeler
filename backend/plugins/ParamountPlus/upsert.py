# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.ParamountPlus.helpers import HelperMixin


class UpsertMixin(HelperMixin, register=False):
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
        self._set_weekly_updates_from_episodes(show, update_show=False)
        return show

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            first_season = self._season_numbers(show_key)[0]
            first_episode = self._season_episodes(show_key, first_season)[0]
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=first_episode.series_title,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=first_episode.thumb.large,
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=7),
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                MediaType.tv,
            )

        self._upsert_tv_seasons(show, force=force)

        return show

    def _upsert_tv_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(show.key)):
            season_key = self._season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, force=force):
                episodes = self._season_episodes(show.key, season_number)
                new_season = Season(
                    key=season_key,
                    name=episodes[0].season_title if episodes else None,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key),
                    season_identifier=self._fallback_season_identifier(season_key),
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

            self._upsert_tv_episodes(season, show.key, season_number, force=force)

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
            episode_key = item.content_id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
                key=episode_key,
                name=item.title,
                episode_number=int(item.episode_number),
                url=item.url,
                description=item.description,
                image_url=item.thumb.large,
                duration=item.duration_raw,
                release_date=item.airdate_iso,
                air_date=item.airdate_iso,
                sort_order=sort_order,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
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

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        movie = self._movie_model(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=movie.name,
                description=movie.description,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=movie.image,
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=30),
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

    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._season_key(show.key, 0)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._movie_url(show.key),
                season_identifier=self._fallback_season_identifier(season_key),
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

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, force=force):
            movie = self._movie_model(show_key)
            new_episode = Episode(
                key=show_key,
                name=movie.name,
                description=movie.description,
                url=self._movie_url(show_key),
                image_url=movie.image,
                episode_number=0,
                sort_order=0,
                release_date=movie.date_published,
                episode_identifier=f"{self.plugin_key()} {show_key}",
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
