# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Tubi.helpers import HelperMixin

_SERIES_UPDATE_INTERVAL = timedelta(days=7)


_MOVIE_UPDATE_INTERVAL = timedelta(days=30)


class UpsertMixin(HelperMixin, register=False):
    @override
    def upsert_show(
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
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            content = self._content(show_key)
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="TV Show",
                url=self._series_url(show_key),
                image_url=self._first_image(content.backgrounds),
                show_identifier=self._fallback_show_identifier(show_key),
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

    def _upsert_series_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_content in enumerate(self._seasons(show.key)):
            season_key = self._season_key(show.key, season_content.id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_content.title,
                    season_number=int(season_content.id),
                    sort_order=sort_order,
                    url=self._series_url(show.key),
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
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
                key=episode_key,
                name=self._episode_name(episode_content.title),
                description=episode_content.description,
                episode_number=int(episode_content.episode_number),
                url=self._episode_url(episode_key),
                image_url=self._first_image(episode_content.thumbnails),
                duration=episode_content.duration,
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
        content = self._content(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
                show_identifier=self._fallback_show_identifier(show_key),
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
            content = self._content(show_key)
            new_episode = Episode(
                key=show_key,
                name=content.title,
                description=content.description,
                episode_number=0,
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
                duration=content.duration,
                sort_order=0,
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
