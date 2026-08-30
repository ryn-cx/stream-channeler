# TODO: Validate
"""Writing what Disney+ says about a title into the database."""

from __future__ import annotations

from typing import override

from app.episodes.models import Episode
from app.models import staggered_update_at
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.service import add_canonical_show_and_link_episodes
from app.sources.models import Source
from plugins.DisneyPlus.source import SourceMixin
from plugins.DisneyPlus.utils import required_value


# TODO: Validate
class UpsertMixin(SourceMixin, register=False):
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
        if self._is_movie(show_key):
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
            details = self._media_details(show_key)
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
                year=self._release_year(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=staggered_update_at(show_key, data_timestamp),
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_tv_seasons(show, force=force)

        return show

    # TODO: Validate
    def _upsert_tv_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_entry in enumerate(self._seasons(show.key)):
            season_id = str(season_entry.id)
            season_key = self._season_key(show.key, season_id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=self._season_number_from_name(
                        season_entry.name,
                        sort_order + 1,
                    ),
                    sort_order=sort_order,
                    data_timestamp=self.season_data_timestamp(season_key, show.key),
                    show_id=show.id,
                )
                season = self._upsert_season_object(new_season, show, season, show.key)

            self._upsert_tv_episodes(season, show.key, season_id, force=force)

    # TODO: Validate
    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self._season_episodes(show_key, season_id)):
            episode_key = str(item.field_id)
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
                name=item.title,
                episode_number=sort_order + 1,
                url=self._video_url(episode_key),
                description=item.metadata.summary,
                image_url=item.image_variants.default_image.source,
                thumbnail_url=item.image_variants.default_image.source,
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
    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        details = self._media_details(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="Movie",
                url=self._show_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
                year=self._release_year(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=staggered_update_at(show_key, data_timestamp),
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_movie_season(show, force=force)

        return show

    # TODO: Validate
    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._season_key(show.key, show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=self.season_data_timestamp(season_key, show.key),
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show.key)

        self._upsert_movie_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            details = self._media_details(show_key)
            new_episode = Episode(
                key=show_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                url=self._video_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
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
