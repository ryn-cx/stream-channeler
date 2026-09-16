# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season as SeasonModel
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.HiDive.constants import (
    SEASON_URL_REGEX,
    SERIES_MEDIA_TYPE,
    SERIES_URL_REGEX,
)
from plugins.HiDive.shared import HiDiveShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from diving_board.season import models as season_models
    from diving_board.series import models as series_models

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class HiDiveSeriesFiles(HiDiveShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.series_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # The season file detects new episodes and changes to the season.
        return [self.season_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The vod file detects changes to the episode information.
        return [self.vod_file(episode_key), self.season_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        series_data = self.series_file(title_key).parsed()
        return [str(item.id) for item in self.series_season_items(series_data)]

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
        for season_key in season_keys:
            bucket = self.season_bucket(self.season_file(season_key).parsed())
            episode_keys.extend(str(item.id) for item in bucket.attributes.items or [])
        return episode_keys

    # TODO: Validate
    @classmethod
    def season_bucket(
        cls,
        season_data: season_models.SeasonModel,
    ) -> season_models.Element:
        """Return the element a season's own episodes are listed in."""
        return cls.single_element(
            [
                element
                for element in season_data.elements
                if element.attributes.type == "season"
            ],
            "bucket",
        )

    # TODO: Validate
    @classmethod
    def series_season_items(
        cls,
        series_data: series_models.SeriesModel,
    ) -> list[series_models.Item1]:
        """Return the list of seasons from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.seasons:
                return element.attributes.seasons.items
        msg = "No seasons element found in series file."
        raise ValueError(msg)


# TODO: Validate
class HiDiveSeriesChannels(HiDiveSeriesFiles, ABC):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.series_title_url(title_key)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        elements = self.series_file(title.key).parsed().elements
        self.add_new_urls_to_channel(
            "All Titles",
            [title.url, *self.related_title_urls(elements)],
        )


# TODO: Validate
class HiDiveSeriesUpsert(HiDiveSeriesChannels, ABC):
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
            series_data = self.series_file(title_key).parsed()
            title = Title(
                key=title_key,
                name=series_data.metadata.series.title,
                media_type=SERIES_MEDIA_TYPE,
                url=self.title_url(title_key),
                image_url=self.series_image_url(series_data),
                thumbnail_url=self.series_image_url(series_data),
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        series_data = self.series_file(title.key).parsed()
        for sort_order, season_info in enumerate(self.series_season_items(series_data)):
            season_key = str(season_info.id)
            hero = self.season_hero(self.season_file(season_key).parsed())

            season = SeasonModel.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=self.season_url(season_key),
                    image_url=self.hero_image_url(hero),
                    thumbnail_url=self.hero_image_url(hero),
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(season, title.key, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: SeasonModel,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        bucket = self.season_bucket(self.season_file(season.key).parsed())
        for sort_order, item in enumerate(bucket.attributes.items or []):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                hero = self.vod_hero(self.vod_file(episode_key).parsed())
                episode = Episode(
                    key=episode_key,
                    watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                    name=item.title,
                    episode_number=self.episode_number(item.title),
                    url=self.episode_url(episode_key),
                    description=item.description,
                    image_url=item.thumbnail_url,
                    thumbnail_url=item.thumbnail_url,
                    duration=item.duration,
                    sort_order=sort_order,
                    air_date=self.release_date(hero),
                    data_timestamp=self._episode_files_data_timestamp(
                        episode_key,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(None)

    # TODO: Validate
    @classmethod
    def season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    # TODO: Validate
    @classmethod
    def season_hero(
        cls,
        season_data: season_models.SeasonModel,
    ) -> season_models.Element:
        """Return the hero element of a parsed season file."""
        return cls.single_element(season_data.elements, "hero")

    # TODO: Validate
    @classmethod
    def series_image_url(cls, series_data: series_models.SeriesModel) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.image:
                return element.attributes.image.attributes.source
        msg = "No image element found in series file."
        raise ValueError(msg)

    # TODO: Validate
    @classmethod
    def episode_number(cls, title: str | None) -> int | None:
        # TODO: Double check there really is no better way to get this information.
        # HiDive puts the episode number as an E## prefix in the title.
        match = re.match(r"^E(\d+)", title) if title else None
        return int(match.group(1)) if match else None


# TODO: Validate
class HiDiveSeriesImporter(HiDiveSeriesUpsert):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, SEASON_URL_REGEX)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return ParsedURL(title_key)

        # HiDive's interface does not do a good job of seperating titles and seasons
        # and if a user uses a season URL it should be treated the same as a series
        # URL for a more intuitive user experience.
        if match := re.match(domain_regex + SEASON_URL_REGEX, url):
            season_key = match.group("season_key")
            season_file = self.season_file(season_key)
            self.raise_invalid_url_if_no_content(season_file, url)
            return ParsedURL(str(season_file.parsed().metadata.series.series_id))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
