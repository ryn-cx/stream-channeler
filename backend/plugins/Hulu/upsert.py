# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from wholoo.movies.models import MoviesModel

from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Hulu.helpers import HelperMixin


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
        return show

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        data_timestamp = self.show_data_timestamp(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            model = self._series_model(show_key)
            entity = model.details.entity
            new_show = Show(
                key=show_key,
                name=model.name,
                description=entity.description,
                media_type="TV Show",
                url=self._show_url(show_key, "series"),
                image_url=self._image_url(model.artwork.program_tile.path),
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
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
        show.set_update_at(data_timestamp + timedelta(days=30))

        return show

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        model = self._movie_model(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            new_show = Show(
                key=show_key,
                name=model.name,
                description=model.details.entity.description,
                url=self._show_url(show_key, "movie"),
                image_url=self._image_url(model.artwork.program_tile.path),
                media_type="Movie",
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=self.show_data_timestamp(show_key),
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
                new_season = Season(
                    key=season_key,
                    name=self._season_name(show.key, season_number),
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key, "series"),
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

    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        model = self._movie_model(show.key)
        season_key = self._season_key(show.key, 0)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show.key, "movie"),
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

        self._upsert_movie_episode(season, show.key, model, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        now = tz_datetime.now()
        for sort_order, item in enumerate(self._season_items(show_key, season_number)):
            start_date = item.bundle.availability.start_date
            if start_date > now:
                season.set_update_at(start_date)
                continue

            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
                key=episode_key,
                name=item.name,
                episode_number=int(item.number),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=self._image_url(item.artwork.video_horizontal_hero.path),
                duration=item.duration,
                release_date=item.premiere_date,
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

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        model: MoviesModel,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, force=force):
            new_episode = Episode(
                key=show_key,
                name=model.name,
                description=model.details.entity.description,
                url=self._episode_url(show_key),
                image_url=self._image_url(model.artwork.program_tile.path),
                duration=model.details.entity.duration,
                episode_number=0,
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
