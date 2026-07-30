# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import Literal, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin


class UpsertMixin(HelperMixin, register=False):
    def _upsert_source(self) -> Source:
        # If this is the first time the source is upserted an initial browse file needs
        # to be downloaded.
        if not (latest_browse_file := self.get_newest_browse_file()):
            latest_browse_file = self.browse_series_file(tz_datetime.now())
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + timedelta(days=1),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show: Show
        tmdb_media_type: Literal["movie", "tv"]
        if show_check := self._show_check(source, show_key, force=force):
            series_data = self.series_file(show_key).parsed().data[0]
            tmdb_media_type = self._series_tmdb_media_type(series_data)
            show = Show(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if tmdb_media_type == "movie" else "Series",
                url=self._show_url(series_data.id),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                show,
                source,
                show_check.record,
                show_key,
                tmdb_media_type,
            )
        else:
            show = show_check.record
            tmdb_media_type = self._show_tmdb_media_type(show)

        self._upsert_seasons(show, tmdb_media_type, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_seasons(
        self,
        show: Show,
        tmdb_media_type: Literal["movie", "tv"],
        *,
        force: bool = False,
    ) -> None:
        seasons_file = self.seasons_file(show.key)
        for index, season_data in enumerate(seasons_file.parsed().data):
            season: Season
            if season_check := self._season_check(
                show,
                season_data.id,
                show.key,
                force=force,
            ):
                season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=index,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    season,
                    show,
                    season_check.record,
                    show.key,
                    tmdb_media_type,
                )
            else:
                season = season_check.record

            self._upsert_episodes(season, show.key, tmdb_media_type, force=force)

    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        tmdb_media_type: Literal["movie", "tv"],
        *,
        force: bool = False,
    ) -> None:
        episodes_data = self.season_episodes_file(season.key).parsed()
        for index, episode_data in enumerate(episodes_data.data):
            episode_check = self._episode_check(
                episode_data.id,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue
            episode = Episode(
                key=episode_data.id,
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self._episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                duration=episode_data.duration_ms // 1000,
                sort_order=index,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                episode_identifier=f"{self.plugin_key()} {episode_data.id}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            self._merge_and_upsert_episode(
                episode,
                season,
                episode_check.record,
                show_key,
                tmdb_media_type,
            )
