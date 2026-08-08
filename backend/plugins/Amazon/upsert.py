# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import override

from app.episodes.models import Episode
from app.media.media_type import MediaType
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
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        return self._upsert_shows(source, show_key, force=force)[0]

    def _upsert_shows(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> list[Show]:
        """Upsert a title into every source it belongs to.

        A title that can be watched more than one way belongs to a source for each
        of them, so it is found however the user can watch it.
        """
        shows = [
            self._upsert_title(title_source, show_key, force=force)
            for title_source in self._title_sources(show_key, source)
        ]
        self._soft_delete_missing(show_key)
        for show in shows:
            self._set_weekly_updates_from_episodes(show, update_show=False)
        return shows

    def _upsert_title(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if self._is_movie(show_key):
            return self._upsert_movie(source, show_key, force=force)
        return self._upsert_series_show(source, show_key, force=force)

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_page(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=page.series_title(),
                description=page.synopsis(),
                media_type="TV Show",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=7),
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
        for sort_order, season_entry in enumerate(self._season_entries(show.key)):
            season_key = season_entry.asin
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, force=force):
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=self._detail_url(season_key),
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
            episode = Episode.get_from_memory(self.session, season, item.asin)
            if not self._episode_is_outdated(episode, force=force):
                continue

            new_episode = Episode(
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
                data_timestamp=self.episode_data_timestamp(
                    item.asin,
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
        page = self.detail_page(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                media_type="Movie",
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                show_identifier=self._fallback_show_identifier(show_key),
                data_timestamp=data_timestamp,
                source_id=source.id,
                update_at=data_timestamp + timedelta(days=30),
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
        season = Season.get_from_memory(self.session, show, show.key)
        if self._season_is_outdated(season, force=force):
            new_season = Season(
                key=show.key,
                season_number=0,
                sort_order=0,
                url=self._detail_url(show.key),
                season_identifier=self._fallback_season_identifier(show.key),
                data_timestamp=self.season_data_timestamp(show.key, show.key),
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
            page = self.detail_page(show_key)
            new_episode = Episode(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                url=self._detail_url(show_key),
                image_url=page.image_url(),
                episode_number=0,
                sort_order=0,
                release_date=_parse_date(page.release_date()),
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
