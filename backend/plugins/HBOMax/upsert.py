# TODO: Validate
"""Writing what HBO Max says about a title into the database."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from minbo.movie.models import Idref14 as MovieContent

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from plugins.HBOMax.helpers import HelperMixin


# TODO: Validate
class UpsertMixin(HelperMixin, register=False):
    """Mixin containing all upsert functions."""

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
        if self._is_movie():
            show = self._upsert_movie(source, show_key, force=force)
        else:
            show = self._upsert_series_show(source, show_key, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        add_canonical_show_and_link_episodes(self.session, show, canonical_show)
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
            content = self._show_content(show_key)
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=content.image_url_link,
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=30),
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_tv_seasons(show, force=force)

        return show

    # TODO: Validate
    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        content = self._movie_content(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="Movie",
                url=self._movie_url(show_key),
                image_url=content.image_url_link,
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=30),
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_movie_season(show, force=force)

        return show

    # TODO: Validate
    def _upsert_tv_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(show.key)):
            season_key = self._season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                entry = self._season_entry(show.key, season_number)
                new_season = Season(
                    key=season_key,
                    name=entry.title.full,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key),
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show.key,
                )

            self._upsert_tv_episodes(season, show.key, season_number, force=force)

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        content = self._movie_content(show.key)
        season_key = self._season_key(show.key, 0)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._movie_url(show.key),
                data_timestamp=self.season_data_timestamp(season_key, show.key),
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show.key)

        self._upsert_movie_episode(season, show.key, content, force=force)

    # TODO: Validate
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
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            new_episode = Episode(
                key=episode_key,
                name=str(item.title.full),
                episode_number=item.episode_number,
                url=item.episode_url,
                description=item.summary.full,
                image_url=item.images.default,
                air_date=item.offering_dates.start_date,
                sort_order=sort_order,
                data_timestamp=self.episode_data_timestamp(
                    episode_key,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)

    # TODO: Validate
    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        content: MovieContent,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            new_episode = Episode(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                url=self._movie_url(show_key),
                image_url=content.image_url_link,
                episode_number=0,
                sort_order=0,
                data_timestamp=self.episode_data_timestamp(
                    show_key,
                    season.key,
                    show_key,
                ),
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)
