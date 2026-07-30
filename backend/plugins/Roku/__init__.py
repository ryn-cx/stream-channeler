# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Roku.files import content_id
from plugins.Roku.handlers import (
    DetailsURLHandler,
    RokuURLHandler,
    WatchURLHandler,
)
from plugins.Roku.helpers import HelperMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Roku(HelperMixin, URLHandlerPlugin[RokuURLHandler], register=True):
    """The Roku Channel plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[RokuURLHandler], ...]] = (
        DetailsURLHandler,
        WatchURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("The Roku Channel",)
    FAVICON_URL = "https://therokuchannel.roku.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"details/{show_key}")

    @classmethod
    def _video_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series or Movie]\n"
            "> `https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae/fawlty-towers`\n\n"
            "> [!TIP/Episode]\n"
            "> `https://therokuchannel.roku.com/watch/fa455123ce5c5aee995fcf6fd1165e33`\n\n"
        )

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url("search")

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

    @override
    def _upsert_show(
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

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            content = self._content(show_key)
            show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="TV Show",
                url=self._show_url(show_key),
                image_url=content.image_map.detail_poster.path,
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

        self._upsert_tv_seasons(show, show_key, force=force)

        return show

    def _upsert_tv_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(show_key)):
            season_key = self._season_key(show_key, season_number)
            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=self._show_url(show_key),
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    season,
                    show,
                    season_check.record,
                    show_key,
                    "tv",
                )
            else:
                season = season_check.record

            self._upsert_tv_episodes(season, show_key, season_number, force=force)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(show_key, season_number),
        ):
            episode_key = content_id(item.meta.id)
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
                name=item.title,
                episode_number=int(item.episode_number),
                url=self._video_url(episode_key),
                description=item.description,
                image_url=item.image_map.grid.path,
                duration=item.view_options[0].media.duration,
                release_date=item.release_date,
                air_date=item.release_date,
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

    def _upsert_movie(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        content = self._content(show_key)
        if show_check := self._show_check(source, show_key, force=force):
            show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                url=self._show_url(show_key),
                image_url=content.image_map.detail_poster.path,
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

        self._upsert_movie_season(show, show_key, force=force)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._season_key(show_key, 0)
        if season_check := self._season_check(show, season_key, show_key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show_key),
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                season,
                show,
                season_check.record,
                show_key,
                "movie",
            )
        else:
            season = season_check.record

        self._upsert_movie_episode(season, show_key, force=force)

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
            content = self._content(show_key)
            episode = Episode(
                key=show_key,
                name=content.title,
                description=content.description,
                url=self._video_url(show_key),
                image_url=content.image_map.detail_poster.path,
                duration=content.run_time_seconds,
                episode_number=0,
                sort_order=0,
                release_date=content.release_date,
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
