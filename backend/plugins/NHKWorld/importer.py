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
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.NHKWorld.shared import TITLE_URL_REGEX, NHKWorldShared
from plugins.NHKWorld.utils import build_url, image_url, thumbnail_url
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NHKWorldImporter(NHKWorldShared, BaseImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        if match := re.match(self._domain_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_if_invalid_file(self.video_program_file(title_key), url)
            return URLTitleInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        program_file = self.video_program_file(title_key)
        program_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [TMDBLookupInfo(program_file.parsed().title, TMDBMediaType.tv, None)]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title.
        return [self.video_program_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season.
            self.video_program_file(title_key),
            # Required to detect new episodes.
            self.video_episodes_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.video_episodes_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        # There are no seasons on NHK World, but the value returned should still match
        # the value used for Season.key.
        return [title_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
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
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            program = self.video_program_file(title_key).parsed()
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=program.id,
                name=program.title,
                description=program.description,
                url=build_url(program.url),
                image_url=image_url(program.images.portrait),
                thumbnail_url=thumbnail_url(program.images.portrait),
                media_type="Series",
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamps)

        self._upsert_season(title, title_key, force=force)
        self._soft_delete_missing(title_key)
        self.mark_title_for_linking(title)

        return title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, title, title_key)
        if self._season_is_outdated(season, title_key, force=force):
            data_timestamps = self.season_data_timestamps(title_key, title_key)
            new_season = Season(
                key=title_key,
                season_number=1,
                sort_order=0,
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            )
            season = new_season.upsert(title, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episodes(season, title_key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(title_key).items()))
        season_data_timestamps = self.season_data_timestamps(title_key, title_key)
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at, season_data_timestamps)

            episode = Episode.get_from_memory(self.session, season, item.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                item.id,
                season.key,
                title_key,
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
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
