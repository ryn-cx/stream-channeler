# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.shared import NHKWorldShared
from plugins.NHKWorld.utils import build_url, image_url, thumbnail_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NHKWorld(NHKWorldShared, BaseImporter, AbstractPlugin, register=False):
    # TODO: Validate
    @override
    def _create_initial_channel_records(self) -> None:
        self._feed_channel()
        self._process_new_episodes_files(self._sources[self.plugin_name()])

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(update_at)
        self._process_new_episodes_files(source)
        self._upsert_source(source.key)

    # TODO: Validate
    @override
    def search_for_title_url(
        self,
        name: str,
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.titles_search_file(name, 0)
        search_file.download_if_outdated()
        hits = search_file.parsed().hits.hits
        return build_url(hits[0].field_source.url) if hits else None

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(
                self.video_program_file(title_key),
                url,
            )
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

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
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            program = self.video_program_file(title_key).parsed()
            title = Title(
                key=program.id,
                name=program.title,
                description=program.description,
                url=build_url(program.url),
                image_url=image_url(program.images.portrait),
                thumbnail_url=thumbnail_url(program.images.portrait),
                media_type="Series",
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_season(title, title_key, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

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
            season = Season(
                key=title_key,
                season_number=1,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(title_key, title_key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

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
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            episode = Episode.get_from_memory(self.session, season, item.id)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
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
                    data_timestamp=self._episode_files_data_timestamp(
                        item.id,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(None)
