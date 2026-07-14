# TODO: Validate
import re
from datetime import datetime, timedelta
from typing import ClassVar, override

from meshfilm.lodp_title_and_plans_page import models as netflix_models

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Netflix.files import FileMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult


class Netflix(FileMixin, register=True):
    _VERSION = "0.0.1"

    @classmethod
    def import_url_instructions(cls) -> str:
        return "> [!TIP/Title]\n> `https://www.netflix.com/title/80240027`\n\n"

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key = self._parse_url(url)
        self._validate_url(show_key, url)
        show = self._import_show(show_key)
        return [URLImportResult(show=show, is_whitelist=False)]

    @override
    def _parse_url(self, url: str) -> str:
        if match := re.match(self._url_regex(), url):
            return match.group("title_key")
        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, show_key: str, url: str) -> None:
        self._raise_if_invalid_file(self.title_file(show_key), url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key).one_or_none():
            return show

        _cache = self._download_show_files_and_children(show_key)
        return self._upsert_show(self.source, show_key)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        # Example URL: https://www.netflix.com/title/80240027
        return cls._domain_regex() + r"\/title\/(?P<title_key>\d+)(?:\/|$)"

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
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        if self._is_movie(show_key):
            return self._upsert_movie(source, show_key)
        return self._upsert_tv_show(source, show_key)

    def _upsert_tv_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        show_data = self._title_video(show_key)
        data_timestamp = self.show_data_timestamp(show_key)

        show = Show(
            key=show_key,
            name=show_data.title,
            description=show_data.short_synopsis,
            url=self._show_url(show_key),
            image_url=show_data.billboard_or_story_art960.url,
            media_type="TV Show",
            data_timestamp=data_timestamp,
            update_at=self._next_update_at(show_key, data_timestamp),
            source_id=source.id,
        ).upsert(source, existing_show)

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
                    update_at=self._next_update_at(
                        show_key,
                        season_check.data_timestamp,
                    ),
                    show_id=show.id,
                ).upsert(show, season_check.record)
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
        for sort_order,     episode_data in enumerate(
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

            Episode(
                key=episode_key,
                name=episode_data.title,
                description=episode_data.short_synopsis,
                url=self._episode_url(episode_key),
                image_url=episode_data.merch_still300.url,
                episode_number=episode_data.number,
                sort_order=sort_order,
                duration=episode_data.runtime_sec,
                data_timestamp=episode_check.data_timestamp,
                update_at=self._next_update_at(show_key, episode_check.data_timestamp),
                season_id=season.id,
            ).upsert(season, episode_check.record)

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
        ).upsert(source, existing_show)

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
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                url=self._show_url(show_key),
                data_timestamp=season_check.data_timestamp,
                update_at=self._next_update_at(show_key, season_check.data_timestamp),
                show_id=show.id,
            ).upsert(show, season_check.record)
        else:
            season = season_check.record

        episode_key = show_key
        if episode_check := self._episode_check(episode_key, season, show_key):
            Episode(
                key=episode_key,
                name=movie_data.title,
                url=self._episode_url(episode_key),
                image_url=movie_data.billboard_or_story_art960.url,
                episode_number=0,
                sort_order=0,
                data_timestamp=episode_check.data_timestamp,
                update_at=self._next_update_at(show_key, episode_check.data_timestamp),
                season_id=season.id,
            ).upsert(season, episode_check.record)

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
