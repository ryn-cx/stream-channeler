# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Amazon.helpers import HelperMixin


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # DTZ007 - Amazon release dates carry no timezone; localized below.
        parsed = datetime.strptime(value, "%b %d, %Y").date()  # noqa: DTZ007
    except ValueError:
        return None
    return tz_datetime.combine(parsed, datetime.min.time())


class UpsertMixin(HelperMixin, register=False):
    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        source = self._channel_source(show_key, source)
        if self._is_movie(show_key):
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
        page = self.detail_page(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=page.series_title(),
                description=page.synopsis(),
                media_type="TV Show",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=7),
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

        return show

    def _upsert_tv_seasons(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_entry in enumerate(self._season_entries(show.key)):
            season_key = season_entry.asin
            if season_check := self._season_check(
                show,
                season_key,
                show.key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=self._detail_url(season_key),
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

            self._upsert_tv_episodes(season, season_key, show.key, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        season_key: str,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self.detail_page(season_key).episodes()):
            episode_check = self._episode_check(
                item.asin,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            episode = Episode(
                key=item.asin,
                name=item.title,
                episode_number=item.episode_number,
                url=self._detail_url(item.asin),
                description=item.synopsis,
                image_url=item.image_url,
                duration=item.duration,
                release_date=_parse_date(item.release_date),
                air_date=_parse_date(item.release_date),
                sort_order=sort_order,
                episode_identifier=f"{self.plugin_key()} {item.asin}",
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

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_page(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                media_type="Movie",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                update_at=show_check.data_timestamp + timedelta(days=30),
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

    def _upsert_movie_season(
        self,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        if season_check := self._season_check(show, show.key, show.key, force=force):
            season = Season(
                key=show.key,
                season_number=0,
                sort_order=0,
                url=self._detail_url(show.key),
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

    def _upsert_movie_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        if episode_check := self._episode_check(
            show_key,
            season,
            show_key,
            force=force,
        ):
            page = self.detail_page(show_key)
            episode = Episode(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                episode_number=0,
                sort_order=0,
                release_date=_parse_date(page.release_date()),
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
