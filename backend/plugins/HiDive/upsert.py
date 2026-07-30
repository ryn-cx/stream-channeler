# TODO: Validate
from __future__ import annotations

import re
from datetime import datetime
from typing import override

from diving_board.vod import models as vod_models
from diving_board.vod.hero.models import VodHeroModel

from app.episodes.models import Episode
from app.seasons.models import Season as SeasonModel
from app.shows.models import Show
from app.sources.models import Source
from plugins.HiDive.files import (
    diving_board,
)
from plugins.HiDive.helpers import HelperMixin

# TODO: Add support for individual episodes of a series.


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
            show = self._upsert_movie_show(source, show_key, force=force)
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
            series_data = self.series_file(show_key).parsed()
            show = Show(
                key=show_key,
                name=series_data.metadata.series.title,
                media_type="Series",
                url=self._show_url(show_key),
                image_url=self._series_image_url(series_data),
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

        self._upsert_series_seasons(show, force=force)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_movie_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())
            show = Show(
                key=show_key,
                name=self._movie_title(hero),
                description=self._movie_description(hero),
                url=self._show_url(show_key, "Movie"),
                image_url=hero.attributes.image.attributes.source,
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

        self._upsert_movie_seasons(show, force=force)

        return show

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
            hero = diving_board().season.extract_hero(season_data)

            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=self._season_url(season_key),
                    image_url=hero.attributes.image.attributes.source,
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

            self._upsert_series_episodes(season, show.key, force=force)

    def _upsert_movie_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_key in enumerate(
            self._season_keys_from_file(show.key),
        ):
            hero = diving_board().vod.extract_hero(self.vod_file(show.key).parsed())

            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                season = SeasonModel(
                    key=season_key,
                    name=self._movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=self._show_url(show.key, "Movie"),
                    image_url=hero.attributes.image.attributes.source,
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

            self._upsert_movie_episode(season, show.key, force=force)

    def _upsert_series_episodes(
        self,
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season_data = self.season_file(season.key).parsed()
        bucket = diving_board().season.extract_bucket_season(season_data)
        for sort_order, item in enumerate(bucket.attributes.items):
            episode_key = str(item.id)
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            vod_data = self.vod_file(episode_key).parsed()
            release_date = self._extract_release_date(vod_data)
            # TODO: Double check there really is no better way to get this information.
            # HiDive puts the episode number as an E## prefix in the title.
            episode_match = re.match(r"^E(\d+)", item.title) if item.title else None
            episode_number = int(episode_match.group(1)) if episode_match else None

            episode = Episode(
                key=episode_key,
                name=item.title,
                episode_number=episode_number,
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=item.thumbnail_url,
                duration=item.duration,
                sort_order=sort_order,
                release_date=release_date,
                air_date=release_date,
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
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode_key = show_key
        vod_data = self.vod_file(episode_key).parsed()
        hero = diving_board().vod.extract_hero(vod_data)

        if episode_check := self._episode_check(
            episode_key,
            season,
            show_key,
            force=force,
        ):
            release_date = self._extract_release_date(vod_data)

            # TODO: This is ugly
            for content in hero.attributes.content:
                if content.attributes.duration is not None:
                    duration = content.attributes.duration
                    break
            else:
                duration = None

            episode = Episode(
                key=episode_key,
                name=self._movie_title(hero),
                description=self._movie_description(hero),
                url=self._episode_url(episode_key),
                image_url=hero.attributes.image.attributes.source,
                episode_number=0,
                sort_order=0,
                duration=duration,
                release_date=release_date,
                air_date=release_date,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
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

    @staticmethod
    def _extract_release_date(vod_data: vod_models.VodModel) -> datetime | None:
        """Extract the release date from the "Original Premiere" tag in the VOD hero."""
        hero = diving_board().vod.extract_hero(vod_data)
        for content in hero.attributes.content:
            if not content.attributes.tags:
                continue
            for tag in content.attributes.tags:
                text = tag.attributes.text
                if text and text.startswith("Original Premiere: "):
                    date_string = text.removeprefix("Original Premiere: ")
                    return datetime.strptime(date_string, "%B %d, %Y").astimezone()
        return None

    @staticmethod
    def _movie_description(hero: VodHeroModel) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero.attributes.content:
            if content.attributes.text:
                return content.attributes.text
        return None
