# TODO: Validate
"""Writing what Peacock says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.Peacock.constants import EPISODE_URL_REGEX, TITLE_URL_REGEX
from plugins.Peacock.files import ShowFile
from plugins.Peacock.shared import PeacockImporter
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pigeon.show.models import Datum1 as SeasonData
    from pigeon.show.models import Datum2 as EpisodeData
    from pigeon.show.models import ShowModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class PeacockSeriesFiles(PeacockImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    def show_file(self, series_id: str) -> ShowFile:
        """Contains all of a series' data (the series, its seasons and its episodes)."""
        return self._cached_file(ShowFile, series_id)

    # TODO: Validate
    def _show(self, title_key: str) -> ShowModel:
        return self.show_file(title_key).parsed()

    # TODO: Validate
    def _seasons(self, title_key: str) -> list[SeasonData]:
        return self.seasons(self._show(title_key))

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_id: str) -> list[EpisodeData]:
        return self.season_episodes(self._show(title_key), season_id)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the series and new seasons of it.
        return [self.show_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # Every season comes down with the series' own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.show_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.show_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            self.build_season_key(title_key, season.attributes.provider_season_id)
            for season in self._seasons(title_key)
        ]

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
            _title_key, season_id = self.split_season_key(season_key)
            episode_keys += [
                str(episode.attributes.provider_variant_id)
                for episode in self._season_episodes(title_key, season_id)
            ]
        return episode_keys

    # TODO: Validate
    @staticmethod
    def seasons(show: ShowModel) -> list[SeasonData]:
        return show.relationships.items.data

    # TODO: Validate
    @staticmethod
    def episodes(season: SeasonData) -> list[EpisodeData]:
        return season.relationships.items.data

    # TODO: Validate
    @classmethod
    def season_episodes(cls, show: ShowModel, season_id: str) -> list[EpisodeData]:
        for season in cls.seasons(show):
            if season.attributes.provider_season_id == season_id:
                return cls.episodes(season)
        return []


# TODO: Validate
class PeacockSeriesUpsert(PeacockSeriesFiles, PeacockImporter, ABC):
    # TODO: Validate
    @override
    def _media_type_channel_key(self) -> str:
        return "Series"

    # TODO: Validate
    @override
    def _genres(self, title_key: str) -> list[str]:
        return self._show(title_key).attributes.genres

    # TODO: Validate
    @override
    def _recommendation_urls(self, title_key: str) -> list[str]:
        return self.show_recommendation_urls(self._show(title_key))

    # TODO: Validate
    @classmethod
    def show_recommendation_urls(cls, show: ShowModel) -> list[str]:
        return [
            cls.asset_url(item.attributes.slug) for item in show.relationships.recs.data
        ]

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.show_file(title_key), url)
            return ParsedURL(title_key, episode_key=match.group("episode_key"))

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.show_file(title_key), url)
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
        show = self._show(title_key)
        attributes = show.attributes
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=attributes.title,
            description=attributes.synopsis_long,
            media_type=MediaType.series,
            year=self.premiere_year(show),
            url=self.asset_url(attributes.slug),
            image_url=self.landscape_url(attributes.images),
            thumbnail_url=self.landscape_url(attributes.images),
            poster_url=self.poster_url(attributes.images),
            poster_thumbnail_url=self.poster_url(attributes.images),
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(attributes.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    @classmethod
    def premiere_year(cls, show: ShowModel) -> int | None:
        """Return the year of the oldest episode, a series having no year of its own."""
        years = [
            episode.attributes.year
            for season in cls.seasons(show)
            for episode in cls.episodes(season)
            if episode.attributes.year is not None
        ]
        return min(years) if years else None

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_data in enumerate(self._seasons(title.key)):
            season_id = season_data.attributes.provider_season_id
            season_key = self.build_season_key(title.key, season_id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=season_data.attributes.title,
                season_number=season_data.attributes.season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, season_id)
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_id: str,
    ) -> None:
        for sort_order, episode_data in enumerate(
            self._season_episodes(title_key, season_id),
        ):
            attributes = episode_data.attributes
            episode_key = str(attributes.provider_variant_id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=attributes.title,
                description=attributes.synopsis,
                episode_number=attributes.episode_number,
                url=self.asset_url(attributes.slug),
                image_url=self.landscape_url(attributes.images),
                thumbnail_url=self.landscape_url(attributes.images),
                duration=attributes.duration_seconds,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)
            season.set_update_at(
                tz_datetime.fromtimestamp(
                    attributes.formats.hd.availability.offer_end_ts / 1000,
                ),
            )


# TODO: Validate
class PeacockSeriesImporter(PeacockSeriesUpsert):
    pass
