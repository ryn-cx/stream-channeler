# TODO: Validate
"""Writing what Hulu says about a title into the database."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from wholoo.movies.models import MoviesModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Hulu.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.Hulu.utils import HelperMixin


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
                url=self._show_url(show_key, SERIES_MEDIA_TYPE),
                image_url=self._image_url(model.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(model.artwork.program_tile.path),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_tv_seasons(show, force=force)
        show.set_update_at(data_timestamp + timedelta(days=30))

        return show

    # TODO: Validate
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
                url=self._show_url(show_key, MOVIE_MEDIA_TYPE),
                image_url=self._image_url(model.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(model.artwork.program_tile.path),
                media_type="Movie",
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
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
                new_season = Season(
                    key=season_key,
                    name=self._season_name(show.key, season_number),
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show.key, SERIES_MEDIA_TYPE),
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(new_season, show, season, show.key)

            self._upsert_tv_episodes(season, show.key, season_number, force=force)

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        model = self._movie_model(show.key)
        season_key = self._season_key(show.key, 0)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show.key, MOVIE_MEDIA_TYPE),
                data_timestamp=self.season_data_timestamp(season_key, show.key),
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show.key)

        self._upsert_movie_episode(season, show.key, model, force=force)

    # TODO: Validate
    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self._season_items(show_key, season_number)):
            start_date = item.bundle.availability.start_date
            if start_date > tz_datetime.now():
                season.set_update_at(start_date)
                continue

            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            hero_artwork = item.artwork.video_horizontal_hero
            new_episode = Episode(
                key=episode_key,
                name=item.name,
                episode_number=int(item.number),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=self._image_url(hero_artwork.path) if hero_artwork else None,
                thumbnail_url=self._thumbnail_url(hero_artwork.path) if hero_artwork else None,
                duration=item.duration,
                air_date=item.premiere_date,
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
        model: MoviesModel,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            new_episode = Episode(
                key=show_key,
                name=model.name,
                description=model.details.entity.description,
                url=self._episode_url(show_key),
                image_url=self._image_url(model.artwork.program_tile.path),
                thumbnail_url=self._thumbnail_url(model.artwork.program_tile.path),
                duration=model.details.entity.duration,
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
