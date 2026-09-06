# TODO: Validate
"""Writing what The Roku Channel says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Roku.shared import DETAILS_URL_REGEX, WATCH_URL_REGEX, RokuShared
from plugins.Roku.utils import (
    build_season_key,
    content_id,
    first_episode_key,
    season_episodes,
    season_numbers,
    show_url,
    split_season_key,
    video_url,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nana.content.models import ContentModel
    from nana.content.models import Episode2 as SeasonEpisode

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class RokuMedia(RokuShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (DETAILS_URL_REGEX, WATCH_URL_REGEX)

    # TODO: Validate
    def _content(self, content_key: str) -> ContentModel:
        return self.content_file(content_key).parsed()

    # TODO: Validate
    def _url_content_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                key = match.group(1)
                self.raise_if_invalid_file(self.content_file(key), url)
                return key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _tmdb_lookup_info(
        self,
        show_key: str,
        media_type: TMDBMediaType,
    ) -> list[TMDBLookupInfo]:
        self.content_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        content = self._content(show_key)
        return [TMDBLookupInfo(content.title, media_type, content.release_year)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]


# TODO: Validate
class RokuSeries(RokuMedia):
    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        key = self._url_content_key(url)
        series = self._content(key).series
        if series is None:
            return MediaInfo(key)

        # A season carries its number after its id, an episode does not, and only
        # an episode is a title of its own to point at.
        show_key = content_id(series.meta.id)
        if "-" in key:
            return MediaInfo(show_key)
        return MediaInfo(show_key, episode_key=key)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.tv)

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[SeasonEpisode]:
        episode_key = first_episode_key(self._content(show_key), season_number)
        return season_episodes(self.season_episodes_file(episode_key).parsed())

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _show_key, season_number = split_season_key(season_key)
        episode_key = first_episode_key(self._content(show_key), season_number)
        return [self.season_episodes_file(episode_key)]

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
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season_number)
            for season_number in season_numbers(self._content(show_key))
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
            _show_key, season_number = split_season_key(season_key)
            episode_keys += [
                content_id(episode.meta.id)
                for episode in self._season_episodes(show_key, season_number)
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
            content = self._content(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Series",
                url=show_url(show_key),
                image_url=content.image_map.detail_poster.path,
                thumbnail_url=content.image_map.detail_poster.path,
                year=content.release_year,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self._content(show.key)),
        ):
            season_key = build_season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, show.key, season_number, force=force)

    # TODO: Validate
    def _upsert_episodes(
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
                name=item.title,
                episode_number=int(item.episode_number),
                url=video_url(episode_key),
                description=item.description,
                image_url=item.image_map.grid.path,
                thumbnail_url=item.image_map.grid.path,
                duration=item.view_options[0].media.duration,
                air_date=item.release_date,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class RokuMovie(RokuMedia):
    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        return MediaInfo(self._url_content_key(url))

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.movie)

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [build_season_key(show_key, 0)]

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
        content = self._content(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                url=show_url(show_key),
                image_url=content.image_map.detail_poster.path,
                thumbnail_url=content.image_map.detail_poster.path,
                year=content.release_year,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                staggered_monthly_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(self, show: Show, *, force: bool = False) -> None:
        season_key = build_season_key(show.key, 0)
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

        self._upsert_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_episode(
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

        content = self._content(show_key)
        data_timestamps = self.episode_data_timestamps(show_key, season.key, show_key)
        new_episode = Episode(
            key=show_key,
            watch_identifier=watch_identifier(self.plugin_name(), show_key),
            name=content.title,
            description=content.description,
            url=video_url(show_key),
            image_url=content.image_map.detail_poster.path,
            thumbnail_url=content.image_map.detail_poster.path,
            duration=content.run_time_seconds,
            episode_number=0,
            sort_order=0,
            air_date=content.release_date,
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
