# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar, override

from meshfilm.lodp_title_and_plans_page import models as netflix_models

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Netflix.helpers import HelperMixin
from plugins.TMDB.mixin import highest_episode_number


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
            show = self._upsert_tv_show(source, show_key, force=force)
        self._soft_delete_missing(show_key)
        return show

    def _upsert_tv_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            show_data = self._title_video(show_key)
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=show_data.title,
                description=show_data.short_synopsis,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=show_data.billboard_or_story_art960.url,
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                update_at=self._next_update_at(show_key, data_timestamp),
                source_id=source.id,
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
        for sort_order, season_data in enumerate(self._ordered_seasons(show.key)):
            season_key = self._season_key(show.key, season_data.video_id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_data.title,
                    season_number=sort_order + 1,
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

            self._upsert_tv_episodes(
                season,
                show.key,
                season_data.video_id,
                force=force,
            )

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: int,
        *,
        force: bool = False,
    ) -> None:
        episodes = self._season_episodes(show_key, season_id)
        last_number = highest_episode_number(
            episode_data.number for episode_data in episodes
        )
        for sort_order, episode_data in enumerate(episodes):
            episode_key = str(episode_data.video_id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
                key=episode_key,
                name=episode_data.title,
                episode_number=episode_data.number,
                url=self._episode_url(episode_key),
                description=episode_data.short_synopsis,
                image_url=episode_data.merch_still300.url,
                duration=episode_data.runtime_sec,
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
                last_number,
            )

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        movie_data = self._title_video(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=movie_data.title,
                url=self._show_url(show_key),
                image_url=movie_data.billboard_or_story_art960.url,
                media_type="Movie",
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                update_at=self._next_update_at(show_key, data_timestamp),
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                MediaType.movie,
            )

        self._upsert_movie_season(show, movie_data, force=force)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        movie_data: netflix_models.Video1,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._season_key(show.key, show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
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
                MediaType.movie,
            )

        episode_key = show.key
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if self._episode_is_outdated(episode, force=force):
            new_episode = Episode(
                key=episode_key,
                name=movie_data.title,
                url=self._episode_url(episode_key),
                image_url=movie_data.billboard_or_story_art960.url,
                episode_number=0,
                sort_order=0,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
                data_timestamp=self.episode_data_timestamp(
                    episode_key,
                    season.key,
                    show.key,
                ),
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                new_episode,
                season,
                episode,
                show.key,
                MediaType.movie,
            )

    _WEEKDAYS: ClassVar[dict[str, int]] = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    def _upcoming_weekday(self, show_key: str) -> int | None:
        """The weekday an upcoming episode is scheduled for, or None if none.

        Netflix surfaces this as a tagline message (e.g. "New Episode Coming
        Thursday"); a title with nothing upcoming has an empty tagline.
        """
        for tagline in self._title_video(show_key).tagline_messages:
            for name, weekday in self._WEEKDAYS.items():
                if name in tagline.tagline:
                    return weekday
        return None

    def _next_update_at(self, show_key: str, data_timestamp: datetime) -> datetime:
        """When to next refresh the title.

        While an episode is upcoming, refresh on the day it is scheduled; if that
        day is the current day, refresh the following day instead. Otherwise refresh
        monthly.
        """
        weekday = self._upcoming_weekday(show_key)
        if weekday is None:
            return data_timestamp + timedelta(days=30)
        days_ahead = (weekday - data_timestamp.weekday()) % 7
        # The scheduled day is the current day, so check again the following day.
        if days_ahead == 0:
            days_ahead = 1
        return data_timestamp + timedelta(days=days_ahead)
