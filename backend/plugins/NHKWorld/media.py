# TODO: Validate
"""Writing what NHK World says about a title into the database."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.NHKWorld.shared import SHOW_URL_REGEX, NHKWorldShared
from plugins.NHKWorld.utils import build_url, image_url, thumbnail_url
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class NHKWorldMedia(NHKWorldShared, BaseImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SHOW_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + SHOW_URL_REGEX, url):
            show_key = match.group("show_key")
            self.raise_if_invalid_file(self.video_program_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        program_file = self.video_program_file(show_key)
        program_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [TMDBLookupInfo(program_file.parsed().title, TMDBMediaType.tv, None)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show.
        return [self.video_program_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season.
            self.video_program_file(show_key),
            # Required to detect new episodes.
            self.video_episodes_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.video_episodes_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        # There are no seasons on NHK World, but the value returned should still match
        # the value used for Season.key.
        return [show_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            item.id
            for season_key in season_keys
            for item in self.video_episodes_file(season_key).items()
        ]

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
            program = self.video_program_file(show_key).parsed()
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=program.id,
                name=program.title,
                description=program.description,
                url=build_url(program.url),
                image_url=image_url(program.images.portrait),
                thumbnail_url=thumbnail_url(program.images.portrait),
                media_type="Series",
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_season(show, show_key, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, show_key)
        if self._season_is_outdated(season, show_key, force=force):
            data_timestamps = self.season_data_timestamps(show_key, show_key)
            new_season = Season(
                key=show_key,
                season_number=1,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(show_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            episode = Episode.get_from_memory(self.session, season, item.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                item.id,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=item.id,
                watch_identifier=watch_identifier(self.plugin_name(), item.id),
                name=item.title,
                url=build_url(item.url),
                description=item.description,
                image_url=image_url(item.images),
                thumbnail_url=thumbnail_url(item.images),
                air_date=item.first_broadcasted_at,
                duration=item.video.duration,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
