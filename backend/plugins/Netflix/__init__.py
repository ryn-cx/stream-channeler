# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar, override
from urllib.parse import quote_plus

from meshfilm.lodp_title_and_plans_page import models as netflix_models

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Netflix.files import FileMixin
from plugins.Netflix.handlers import NetflixURLHandler, TitleURLHandler
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin

_SEARCH_MAX_AGE = timedelta(days=30)


class Netflix(FileMixin, URLHandlerPlugin[NetflixURLHandler], register=True):
    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Netflix", "Netflix Standard with Ads")

    _URL_HANDLERS: ClassVar[tuple[type[NetflixURLHandler], ...]] = (TitleURLHandler,)

    # Netflix tags each search result with the media type of its title.
    _SEARCH_MEDIA_TYPES: ClassVar[dict[str, str]] = {
        "Show": "TV Show",
        "Movie": "Movie",
    }

    @classmethod
    @override
    def search_url(cls, query: str) -> str:
        return f"https://www.netflix.com/search?q={quote_plus(query)}"

    @override
    def search(self, query: str) -> PluginSearchResults:
        """Search Netflix's movies and TV shows.

        Netflix returns movies and shows intermixed. Suggestion entities
        (collections, autocomplete) carry no title and are skipped.
        """
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)

        results: list[PluginSearchResult] = []
        for section in search_file.parsed().data.page.sections.edges:
            for entity in section.node.entities.edges:
                unified_entity = entity.node.unified_entity
                if unified_entity is None:
                    continue
                media_type = self._SEARCH_MEDIA_TYPES.get(
                    unified_entity.field__typename,
                )
                if media_type is None:
                    continue
                title = entity.node.display_string
                artwork = entity.node.contextual_artwork
                results.append(
                    PluginSearchResult(
                        title=title,
                        url=self._show_url(str(unified_entity.video_id)),
                        image_url=artwork.artwork.url if artwork else None,
                        media_type=media_type,
                    ),
                )
        return PluginSearchResults(results=results)

    @classmethod
    def import_url_instructions(cls) -> str:
        return "> [!TIP/Title]\n> `https://www.netflix.com/title/80240027`\n\n"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"title/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="Netflix",
            favicon_url="https://www.netflix.com/favicon.ico",
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        if self._is_movie(show_key):
            return self._upsert_movie(source, show_key)
        return self._upsert_tv_show(source, show_key)

    def _upsert_tv_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        show_data = self._title_video(show_key)
        data_timestamp = self.show_data_timestamp(show_key)
        tmdb_id = self._fetch_tmdb_id(show_key, existing_show)

        show = Show(
            key=show_key,
            name=show_data.title,
            description=show_data.short_synopsis,
            media_type="TV Show",
            url=self._show_url(show_key),
            image_url=show_data.billboard_or_story_art960.url,
            data_timestamp=data_timestamp,
            update_at=self._next_update_at(show_key, data_timestamp),
            source_id=source.id,
        )
        show = self.tmdb.tmdb_merge_show(show, tmdb_id)
        show_files = self._show_files(show_key)
        show = show.upsert_and_set_update_at(source, existing_show, show_files)

        self._upsert_tv_seasons(show, show_key)
        return show

    def _upsert_tv_seasons(self, show: Show, show_key: str) -> None:
        for sort_order, season_data in enumerate(self._ordered_seasons(show_key)):
            season_key = self._season_key(show_key, season_data.video_id)
            if season_check := self._season_check(show, season_key, show_key):
                season = Season(
                    key=season_key,
                    name=season_data.title,
                    season_number=sort_order + 1,
                    sort_order=sort_order,
                    url=self._show_url(show_key),
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self.tmdb.tmdb_merge_season(
                    season,
                    show.tmdb_id,
                    sort_order + 1,
                    "tv",
                )
                season_files = self._season_files(season_key, show_key)
                season = season.upsert_and_set_update_at(
                    show,
                    season_check.record,
                    season_files,
                )
            else:
                season = season_check.record

            self._upsert_tv_episodes(season, show_key, season_data.video_id)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_tv_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: int,
    ) -> None:
        for sort_order, episode_data in enumerate(
            self._season_episodes(show_key, season_id),
        ):
            episode_key = str(episode_data.video_id)
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
            )
            if not episode_check:
                continue

            episode = Episode(
                key=episode_key,
                name=episode_data.title,
                episode_number=episode_data.number,
                url=self._episode_url(episode_key),
                description=episode_data.short_synopsis,
                image_url=episode_data.merch_still300.url,
                duration=episode_data.runtime_sec,
                sort_order=sort_order,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            episode = self.tmdb.tmdb_merge_episode(
                episode,
                season.show.tmdb_id,
                season.season_number,
                episode_data.number,
            )
            episode_files = self._episode_files(episode_key, season.key, show_key)
            episode.upsert_and_set_update_at(
                season,
                episode_check.record,
                episode_files,
            )

        self.soft_delete_missing_episodes(season.key)

    def _upsert_movie(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        movie_data = self._title_video(show_key)
        data_timestamp = self.show_data_timestamp(show_key)

        show = Show(
            key=show_key,
            name=movie_data.title,
            url=self._show_url(show_key),
            image_url=movie_data.billboard_or_story_art960.url,
            media_type="Movie",
            data_timestamp=data_timestamp,
            update_at=self._next_update_at(show_key, data_timestamp),
            source_id=source.id,
        ).upsert_and_set_update_at(source, existing_show, self._show_files(show_key))

        self._upsert_movie_season(show, show_key, movie_data)
        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        movie_data: netflix_models.Video1,
    ) -> None:
        season_key = self._season_key(show_key, show_key)
        if season_check := self._season_check(show, season_key, show_key):
            season_files = self._season_files(season_key, show_key)
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show_key),
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            ).upsert_and_set_update_at(show, season_check.record, season_files)
        else:
            season = season_check.record

        episode_key = show_key
        if episode_check := self._episode_check(episode_key, season, show_key):
            episode_files = self._episode_files(episode_key, season.key, show_key)
            Episode(
                key=episode_key,
                name=movie_data.title,
                url=self._episode_url(episode_key),
                image_url=movie_data.billboard_or_story_art960.url,
                episode_number=0,
                sort_order=0,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode_check.record, episode_files)

        self.soft_delete_missing_episodes(season.key)
        self.soft_delete_missing_seasons(show_key)

    _WEEKDAYS: ClassVar[dict[str, int]] = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    def _upcoming_weekday(self, show_key: str) -> int | None:
        """The weekday an upcoming episode is scheduled for, or None if none.

        Netflix surfaces this as a tagline message (e.g. "New Episode Coming
        Thursday"); a title with nothing upcoming has an empty tagline.
        """
        for tagline in self._title_video(show_key).tagline_messages:
            for name, weekday in self._WEEKDAYS.items():
                if name in tagline.tagline:
                    return weekday
        return None

    def _next_update_at(self, show_key: str, data_timestamp: datetime) -> datetime:
        """When to next refresh the title.

        While an episode is upcoming, refresh on the day it is scheduled; if that
        day is the current day, refresh the following day instead. Otherwise refresh
        monthly.
        """
        weekday = self._upcoming_weekday(show_key)
        if weekday is None:
            return data_timestamp + timedelta(days=30)
        days_ahead = (weekday - data_timestamp.weekday()) % 7
        # The scheduled day is the current day, so check again the following day.
        if days_ahead == 0:
            days_ahead = 1
        return data_timestamp + timedelta(days=days_ahead)
