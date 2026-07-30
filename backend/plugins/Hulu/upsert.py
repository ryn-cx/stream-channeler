# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from wholoo.movies.models import MoviesModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Hulu.helpers import HelperMixin


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
            model = self._series_model(show_key)
            entity = model.details.entity
            show = Show(
                key=show_key,
                name=model.name,
                description=entity.description,
                media_type="TV Show",
                url=self._show_url(show_key, "series"),
                image_url=self._image_url(model.artwork.program_tile.path),
                data_timestamp=show_check.data_timestamp,
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

        self._upsert_tv_seasons(show, force=force)
        show.set_update_at(show_check.data_timestamp + timedelta(days=30))

        return show

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        model = self._movie_model(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=model.name,
                description=model.details.entity.description,
                url=self._show_url(show_key, "movie"),
                image_url=self._image_url(model.artwork.program_tile.path),
                media_type="Movie",
                data_timestamp=show_check.data_timestamp,
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
                season = Season(
                    key=season_key,
                    name=self._season_name(show.key, season_number),
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key, "series"),
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
        model = self._movie_model(show.key)
        season_key = self._season_key(show.key, 0)
        if season_check := self._season_check(show, season_key, show.key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show.key, "movie"),
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

        self._upsert_movie_episode(season, show.key, model, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self._season_items(show_key, season_number)):
            season.set_update_at(item.bundle.availability.start_date)
            episode_key = str(item.id)
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
                name=item.name,
                episode_number=int(item.number),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=self._image_url(item.artwork.video_horizontal_hero.path),
                duration=item.duration,
                release_date=item.premiere_date,
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
        model: MoviesModel,
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
                name=model.name,
                description=model.details.entity.description,
                url=self._episode_url(show_key),
                image_url=self._image_url(model.artwork.program_tile.path),
                duration=model.details.entity.duration,
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
