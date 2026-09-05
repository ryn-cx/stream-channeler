# TODO: Validate
"""Writing what Prime Video says about a title into the database."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Amazon.files import FileMixin
from plugins.Amazon.utils import UtilsMixin


# TODO: Validate
def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    # DTZ007 - Amazon release dates carry no timezone; localized below.
    parsed = datetime.strptime(value, "%b %d, %Y").date()  # noqa: DTZ007
    return tz_datetime.combine(parsed, datetime.min.time())


# TODO: Validate
class UpsertMixin(UtilsMixin, FileMixin):
    """Mixin containing all upsert functions."""

    # TODO: Validate
    def _title_url(self, title_key: str) -> str:
        return self._detail_url(self.detail_file(title_key).compact_key())

    # TODO: Validate
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
            show = self._upsert_series_show(source, show_key, force=force)

        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        return show

    # TODO: Validate
    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_file(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=page.series_title(),
                description=page.synopsis(),
                media_type="Series",
                url=self._title_url(show_key),
                image_url=page.image_url(),
                thumbnail_url=page.image_url(),
                year=page.release_year(),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_series_seasons(show, force=force)

        return show

    # TODO: Validate
    def _upsert_series_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_entry in enumerate(self._season_entries(show.key)):
            season_key = season_entry.key
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=self._detail_url(season_key),
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_series_episodes(season, show.key, force=force)

    # TODO: Validate
    def _upsert_series_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episodes = self.detail_file(season.key).episodes()
        for sort_order, item in enumerate(episodes):
            episode = Episode.get_from_memory(self.session, season, item.key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                item.key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=item.key,
                watch_identifier=watch_identifier(self.plugin_name(), item.key),
                name=item.title,
                episode_number=item.episode_number,
                url=self._detail_url(item.compact_key),
                description=item.synopsis,
                image_url=item.image_url,
                thumbnail_url=item.image_url,
                duration=item.duration,
                air_date=_parse_date(item.release_date),
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)

    # TODO: Validate
    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        page = self.detail_file(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=page.title(),
                description=page.synopsis(),
                media_type="Movie",
                url=self._title_url(show_key),
                image_url=page.image_url(),
                thumbnail_url=page.image_url(),
                year=page.release_year(),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(staggered_monthly_update_at(show_key, data_timestamp), data_timestamps)

        self._upsert_movie_season(show, force=force)

        return show

    # TODO: Validate
    def _upsert_movie_season(self, show: Show, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, show, show.key)
        if self._season_is_outdated(season, show.key, force=force):
            data_timestamps = self.season_data_timestamps(show.key, show.key)
            new_season = Season(
                key=show.key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

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
        if not self._episode_is_outdated(
            episode,
            season.key,
            show_key,
            force=force,
        ):
            return

        page = self.detail_file(show_key)
        data_timestamps = self.episode_data_timestamps(show_key, season.key, show_key)
        new_episode = Episode(
            key=show_key,
            watch_identifier=watch_identifier(self.plugin_name(), show_key),
            name=page.title(),
            description=page.synopsis(),
            url=self._title_url(show_key),
            image_url=page.image_url(),
            thumbnail_url=page.image_url(),
            duration=page.duration(),
            episode_number=0,
            sort_order=0,
            air_date=_parse_date(page.release_date()),
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
