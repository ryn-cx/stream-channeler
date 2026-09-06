# TODO: Validate
"""Writing what Netflix says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Netflix.shared import TITLE_URL_REGEX, NetflixShared
from plugins.Netflix.utils import (
    build_season_key,
    episode_url,
    ordered_seasons,
    season_episodes,
    show_url,
    split_season_key,
    title_video,
    upcoming_weekday,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from meshfilm.lodp_title_and_plans_page.models import Video1 as TitleVideo
    from meshfilm.preview_modal_episode_selector.models import Node as SeasonNode
    from meshfilm.preview_modal_episode_selector_season_episodes.models import (
        Node as EpisodeNode,
    )

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NetflixMedia(NetflixShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + TITLE_URL_REGEX, url):
            show_key = match.group("title_key")
            self.raise_if_invalid_file(self.title_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _title_video(self, show_key: str) -> TitleVideo:
        return title_video(self.title_file(show_key).parsed(), show_key)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.title_file(show_key), self.seasons_file(show_key)]

    # TODO: Validate
    def _next_update_at(self, show_key: str, data_timestamp: datetime) -> datetime:
        """When to next refresh the title.

        While an episode is upcoming, refresh on the day it is scheduled; if that
        day is the current day, refresh the following day instead. Otherwise refresh
        monthly.
        """
        weekday = upcoming_weekday(self._title_video(show_key))
        if weekday is None:
            return staggered_monthly_update_at(show_key, data_timestamp)
        days_ahead = (weekday - data_timestamp.weekday()) % 7
        # The scheduled day is the current day, so check again the following day.
        if days_ahead == 0:
            days_ahead = 1
        return data_timestamp + timedelta(days=days_ahead)


# TODO: Validate
class NetflixSeries(NetflixMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        self.title_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        video = self._title_video(show_key)
        return [TMDBLookupInfo(video.title, TMDBMediaType.tv, video.latest_year)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _show_key, season_id = split_season_key(season_key)
        return [self.season_episodes_file(season_id), self.seasons_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_files(season_key, show_key)

    # TODO: Validate
    def _ordered_seasons(self, show_key: str) -> list[SeasonNode]:
        return ordered_seasons(self.seasons_file(show_key).parsed())

    # TODO: Validate
    def _season_episodes(self, season_id: str | int) -> list[EpisodeNode]:
        return season_episodes(self.season_episodes_file(season_id).parsed())

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season.video_id)
            for season in self._ordered_seasons(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            _show_key, season_id = split_season_key(season_key)
            episode_keys += [
                str(episode.video_id) for episode in self._season_episodes(season_id)
            ]
        return episode_keys

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            show_data = self._title_video(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=show_data.title,
                description=show_data.short_synopsis,
                media_type="Series",
                url=show_url(show_key),
                image_url=show_data.billboard_or_story_art960.url,
                thumbnail_url=show_data.billboard_or_story_art960.url,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                self._next_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_data in enumerate(self._ordered_seasons(show.key)):
            season_key = build_season_key(show.key, season_data.video_id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=season_data.title,
                    season_number=sort_order + 1,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(
                season,
                show.key,
                season_data.video_id,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_data in enumerate(self._season_episodes(season_id)):
            episode_key = str(episode_data.video_id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=episode_data.title,
                episode_number=episode_data.number,
                url=episode_url(episode_key),
                description=episode_data.contextual_synopsis.text,
                image_url=episode_data.artwork.url,
                thumbnail_url=episode_data.artwork.url,
                duration=episode_data.runtime_sec,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class NetflixMovie(NetflixMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        self.title_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        video = self._title_video(show_key)
        return [TMDBLookupInfo(video.title, TMDBMediaType.movie, video.latest_year)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [build_season_key(show_key, show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        movie_data = self._title_video(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=movie_data.title,
                url=show_url(show_key),
                image_url=movie_data.billboard_or_story_art960.url,
                thumbnail_url=movie_data.billboard_or_story_art960.url,
                media_type="Movie",
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                self._next_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(show, movie_data, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        movie_data: TitleVideo,
        *,
        force: bool = False,
    ) -> None:
        season_key = build_season_key(show.key, show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, show.key)
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, show.key, movie_data, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        movie_data: TitleVideo,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            data_timestamps = self.episode_data_timestamps(
                show_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=show_key,
                watch_identifier=watch_identifier(self.plugin_name(), show_key),
                name=movie_data.title,
                url=episode_url(show_key),
                image_url=movie_data.billboard_or_story_art960.url,
                thumbnail_url=movie_data.billboard_or_story_art960.url,
                episode_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
