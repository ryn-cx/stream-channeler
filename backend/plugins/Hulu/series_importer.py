# TODO: Validate
"""Writing what Hulu says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Hulu.constants import SERIES_URL_REGEX, VIDEO_URL_REGEX, HuluMediaType
from plugins.Hulu.shared import (
    HuluImporter,
    build_season_key,
    build_url,
    episode_url,
    image_url,
    is_collection_season_key,
    season_items,
    season_numbers,
    split_season_key,
    thumbnail_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wholoo.tv.models import Component as SeriesComponent

    from app.sources.models import Source
    from plugins.Hulu.files import Series
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HuluSeriesFiles(HuluImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return build_url(f"{HuluMediaType.SERIES}/{title_key}")

    # TODO: Validate
    @override
    def _media_type_name(self) -> str:
        return "Series"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[Series]:
        return [self.series_file(title_key)]

    # TODO: Validate
    @override
    def _title_components(self, title_key: str) -> Sequence[SeriesComponent]:
        return self.series_file(title_key).components()

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        if is_collection_season_key(season_key):
            return [self.series_file(title_key)]
        _, season_number = split_season_key(season_key)
        # Includes season information and the list of episodes.
        return [self.season_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_collection_season_key(season_key):
            return [self.series_file(title_key)]
        _, season_number = split_season_key(season_key)
        # Includes episode information.
        return [self.season_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            build_season_key(title_key, season_number)
            for season_number in season_numbers(self.series_file(title_key).parsed())
        ] + self._collection_season_keys(title_key)

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for key in season_keys:
            if is_collection_season_key(key):
                episode_keys += self._collection_episode_keys(key, title_key)
                continue
            title_key, season_number = split_season_key(key)
            episode_keys += [
                str(item.id)
                for item in season_items(
                    self.season_file(title_key, season_number).parsed(),
                )
            ]
        return episode_keys


# TODO: Validate
class HuluSeriesUpsert(HuluSeriesFiles, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return ParsedURL(title_key)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_key")
            episode_file = self.episode_file(episode_key)
            self.raise_invalid_url_if_no_content(episode_file, url)
            return ParsedURL(episode_file.series_key(), episode_key=episode_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _title_record(self, source: Source, title_key: str) -> Title:
        parsed_series = self.series_file(title_key).parsed()
        entity = parsed_series.details.entity
        vertical_tile = parsed_series.artwork.program_vertical_tile
        return Title(
            key=title_key,
            name=parsed_series.name,
            description=entity.description,
            year=entity.premiere_date.year if entity.premiere_date else None,
            # TODO: There are mini series or documentary labels as well that could
            # be intermixed here?
            media_type=MediaType.series,
            url=self.title_url(title_key),
            image_url=image_url(parsed_series.artwork.program_tile.path),
            thumbnail_url=thumbnail_url(parsed_series.artwork.program_tile.path),
            poster_url=image_url(vertical_tile.path if vertical_tile else None),
            poster_thumbnail_url=thumbnail_url(
                vertical_tile.path if vertical_tile else None,
            ),
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        )

    # TODO: Validate
    @override
    def _upsert_title_seasons(self, title: Title) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self.series_file(title.key).parsed()),
        ):
            season_key = build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=(
                    self.season_file(title.key, season_number)
                    .parsed()
                    .series_grouping_metadata.grouping_name
                ),
                season_number=season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season)
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(self, season: Season) -> None:
        title_key, season_number = split_season_key(season.key)
        items = season_items(self.season_file(title_key, season_number).parsed())
        for sort_order, item in enumerate(items):
            episode_key = str(item.id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )

            hero_artwork = item.artwork.video_horizontal_hero
            hero_path = hero_artwork.path if hero_artwork else None
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.name,
                episode_number=int(item.number),
                url=episode_url(episode_key),
                description=item.description,
                image_url=image_url(hero_path),
                thumbnail_url=thumbnail_url(hero_path),
                duration=item.duration,
                air_date=item.premiere_date,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
                update_at=item.premiere_date,
            ).upsert(season, existing_episode)


# TODO: Validate


# TODO: Validate
class HuluSeriesImporter(HuluSeriesUpsert):
    pass
