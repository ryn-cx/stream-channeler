# TODO: Validate
"""Writing what NHK World says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.files import VideoEpisodes
from plugins.NHKWorld.shared import MINIMUM_THUMBNAIL_WIDTH, NHKWorldShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from naphki.video_episodes.models import Image as EpisodeImage
    from naphki.video_program.models import LandscapeItem, PortraitItem

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NHKWorldSeriesUpsert(NHKWorldShared, BaseUpserter, ABC):
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            video_program_file = self.video_program_file(title_key)
            self.raise_invalid_url_if_no_content(video_program_file, url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        program = self.video_program_file(title_key).parsed()
        upserted_title = Title(
            key=program.id,
            name=program.title,
            description=program.description,
            url=self.build_url(program.url),
            image_url=self.image_url(program.images.landscape),
            thumbnail_url=self.thumbnail_url(program.images.landscape),
            poster_url=self.image_url(program.images.portrait),
            poster_thumbnail_url=self.thumbnail_url(program.images.portrait),
            media_type=MediaType.series,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(category.name for category in program.categories)

        self._upsert_season(upserted_title, title_key)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
    ) -> None:
        existing_season = Season.get_from_memory(self.session, title, title_key)
        upserted_season = Season(
            key=title_key,
            season_number=1,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(title_key, title_key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episodes(upserted_season, title_key)
        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(title_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            existing_episode = Episode.get_from_memory(self.session, season, item.id)
            Episode(
                key=item.id,
                watch_identifier=watch_identifier(self.plugin_name(), item.id),
                name=item.title,
                url=self.build_url(item.url),
                description=item.description,
                image_url=self.image_url(item.images),
                thumbnail_url=self.thumbnail_url(item.images),
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
            ).upsert(season, existing_episode)

    # TODO: Validate
    @classmethod
    def image_url(
        cls,
        images: Sequence[LandscapeItem | PortraitItem | EpisodeImage],
    ) -> str:
        largest = max(images, key=lambda image: image.width)
        return cls.build_url(largest.url)

    # TODO: Validate
    @classmethod
    def thumbnail_url(
        cls,
        images: Sequence[LandscapeItem | PortraitItem | EpisodeImage],
    ) -> str:
        wide_enough = [
            image for image in images if image.width >= MINIMUM_THUMBNAIL_WIDTH
        ]
        chosen = (
            min(wide_enough, key=lambda image: image.width)
            if wide_enough
            else max(images, key=lambda image: image.width)
        )
        return cls.build_url(chosen.url)

    # TODO: Validate
    def video_episodes_file(self, program_id: str) -> VideoEpisodes:
        """Contains a title's episodes."""
        return self._cached_file(VideoEpisodes, program_id)

    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Detects changes to the title.
        return [self.video_program_file(title_key)]

    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Detects changes to the season.
            self.video_program_file(title_key),
            # Detects new episodes.
            self.video_episodes_file(title_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Detects changes to the episode.
        return [self.video_episodes_file(title_key)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        # NHK World has no seasons,
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


# TODO: Validate
class NHKWorldSeriesImporter(NHKWorldSeriesUpsert):
    pass
