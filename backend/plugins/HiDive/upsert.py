# TODO: Validate
"""Writing what HiDive says about a title into the database."""

from __future__ import annotations

import re
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season as SeasonModel
from app.shows.models import Show
from app.shows.service import find_and_add_canonical_show
from app.sources.models import Source
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.HiDive.files import season_bucket
from plugins.HiDive.helpers import HelperMixin, season_hero, vod_hero

# TODO: Add support for individual episodes of a series.


# TODO: Validate
def _episode_number(title: str | None) -> int | None:
    # TODO: Double check there really is no better way to get this information.
    # HiDive puts the episode number as an E## prefix in the title.
    match = re.match(r"^E(\d+)", title) if title else None
    return int(match.group(1)) if match else None


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
            show = self._upsert_movie_show(source, show_key, force=force)
        else:
            show = self._upsert_series_show(source, show_key, force=force)
        self._soft_delete_missing(show_key)
        find_and_add_canonical_show(self.session, show, canonical_show)
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
            series_data = self.series_file(show_key).parsed()
            new_show = Show(
                key=show_key,
                name=series_data.metadata.series.title,
                media_type=SERIES_MEDIA_TYPE,
                url=self._show_url(show_key),
                image_url=self._series_image_url(series_data),
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_series_seasons(show, force=force)
        self._set_weekly_updates_from_episodes(show)

        return show

    # TODO: Validate
    def _upsert_movie_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            hero = vod_hero(self.vod_file(show_key).parsed())
            new_show = Show(
                key=show_key,
                name=self._movie_title(hero),
                description=self._movie_description(hero),
                url=self._show_url(show_key, MOVIE_MEDIA_TYPE),
                image_url=self._hero_image_url(hero),
                media_type=MOVIE_MEDIA_TYPE,
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_movie_seasons(show, force=force)

        return show

    # TODO: Validate
    def _upsert_series_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        series_data = self.series_file(show.key).parsed()
        season_items = self._series_season_items(series_data)
        for sort_order, season_info in enumerate(season_items):
            season_key = str(season_info.id)
            season_data = self.season_file(season_key).parsed()
            hero = season_hero(season_data)

            season = SeasonModel.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                new_season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=self._season_url(season_key),
                    image_url=self._hero_image_url(hero),
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show.key,
                )

            self._upsert_series_episodes(season, show.key, force=force)

    # TODO: Validate
    def _upsert_movie_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_key in enumerate(
            self._season_keys_from_file(show.key),
        ):
            hero = vod_hero(self.vod_file(show.key).parsed())

            season = SeasonModel.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                new_season = SeasonModel(
                    key=season_key,
                    name=self._movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=self._show_url(show.key, MOVIE_MEDIA_TYPE),
                    image_url=self._hero_image_url(hero),
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show.key,
                )

            self._upsert_movie_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_series_episodes(
        self,
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season_data = self.season_file(season.key).parsed()
        bucket = season_bucket(season_data)
        for sort_order, item in enumerate(bucket.attributes.items or []):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            hero = vod_hero(self.vod_file(episode_key).parsed())
            new_episode = Episode(
                key=episode_key,
                name=item.title,
                episode_number=_episode_number(item.title),
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=item.thumbnail_url,
                duration=item.duration,
                sort_order=sort_order,
                air_date=self._release_date(hero),
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
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode_key = show_key
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if not self._episode_is_outdated(
            episode,
            season.key,
            show_key,
            force=force,
        ):
            return

        hero = vod_hero(self.vod_file(episode_key).parsed())
        new_episode = Episode(
            key=episode_key,
            name=self._movie_title(hero),
            description=self._movie_description(hero),
            url=self._episode_url(episode_key),
            image_url=self._hero_image_url(hero),
            episode_number=0,
            sort_order=0,
            duration=self._movie_duration(hero),
            air_date=self._release_date(hero),
            data_timestamp=self.episode_data_timestamp(
                episode_key,
                season.key,
                show_key,
            ),
            season_id=season.id,
        )
        self._upsert_episode_object(new_episode, season, episode, show_key)
