# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override
from urllib.parse import quote

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Tubi.handlers import (
    EpisodeURLHandler,
    MovieURLHandler,
    SeriesURLHandler,
    TubiURLHandler,
)
from plugins.Tubi.helpers import HelperMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin

_SERIES_UPDATE_INTERVAL = timedelta(days=7)
_MOVIE_UPDATE_INTERVAL = timedelta(days=30)


class Tubi(HelperMixin, URLHandlerPlugin[TubiURLHandler], register=True):
    """Tubi plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[TubiURLHandler], ...]] = (
        MovieURLHandler,
        SeriesURLHandler,
        EpisodeURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Tubi TV", "Tubi")
    FAVICON_URL = "https://tubitv.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"movies/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"tv-shows/{episode_key}")

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://tubitv.com/series/300006854/scooby-doo-where-are-you`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://tubitv.com/movies/100029837/megamind`\n\n"
            "> [!TIP/Episode]\n"
            "> `https://tubitv.com/tv-shows/595036`\n\n"
        )

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search/{quote(query)}")

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
                url=self._series_url(show_key),
                image_url=self._first_image(content.backgrounds),
                data_timestamp=show_check.data_timestamp,
                update_at=show_check.data_timestamp + _SERIES_UPDATE_INTERVAL,
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

        self._upsert_series_seasons(show, show_key, force=force)

        return show

    def _upsert_series_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_content in enumerate(self._seasons(show_key)):
            season_key = self._season_key(show_key, season_content.id)
            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = Season(
                    key=season_key,
                    name=season_content.title,
                    season_number=int(season_content.id),
                    sort_order=sort_order,
                    url=self._series_url(show_key),
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

            self._upsert_series_episodes(
                season,
                show_key,
                season_content.id,
                force=force,
            )

    def _upsert_series_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_content in enumerate(
            self._season_episodes(show_key, season_id),
        ):
            episode_key = episode_content.id
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
                name=self._episode_name(episode_content.title),
                description=episode_content.description,
                episode_number=int(episode_content.episode_number),
                url=self._episode_url(episode_key),
                image_url=self._first_image(episode_content.thumbnails),
                duration=episode_content.duration,
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
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
                data_timestamp=show_check.data_timestamp,
                update_at=show_check.data_timestamp + _MOVIE_UPDATE_INTERVAL,
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

        self._upsert_movie_season(show, show_key, force=force)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season_key = self._movie_season_key(show_key)
        if season_check := self._season_check(show, season_key, show_key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._movie_url(show_key),
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
                episode_number=0,
                url=self._movie_url(show_key),
                image_url=self._first_image(content.backgrounds),
                duration=content.duration,
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
