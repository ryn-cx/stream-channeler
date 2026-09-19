# TODO: Validate
"""Writing what NHK World says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.shared import (
    NHKWorldImporter,
    build_url,
    image_url,
    thumbnail_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from app.sources.models import Source


# TODO: Validate
class NHKWorldSeriesUpsert(NHKWorldImporter, ABC):
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
            url=build_url(program.url),
            image_url=image_url(program.images.landscape),
            thumbnail_url=thumbnail_url(program.images.landscape),
            poster_url=image_url(program.images.portrait),
            poster_thumbnail_url=thumbnail_url(program.images.portrait),
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
        self.add_title_to_plugin_channels(upserted_title)

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
            ).upsert(season, existing_episode)


# TODO: Validate


# TODO: Validate
class NHKWorldSeriesImporter(NHKWorldSeriesUpsert):
    pass
