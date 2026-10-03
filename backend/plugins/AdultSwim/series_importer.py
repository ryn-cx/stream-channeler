# TODO: Validate
"""Writing what Adult Swim says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.AdultSwim.constants import (
    EPISODE_URL_REGEX,
    SUBSCRIPTION,
    TITLE_URL_REGEX,
)
from plugins.AdultSwim.files import TitlePage
from plugins.AdultSwim.shared import AdultSwimShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pools_closed.show.models import Episode as EpisodeData
    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AdultSwimSeriesUpsert(AdultSwimShared, BaseUpserter, ABC):
    # TODO: Validate
    def title_file(self, title_key: str) -> TitlePage:
        return self._cached_file(TitlePage, title_key)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return self.season_keys(self.title_file(title_key).parsed())

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return self.episode_keys(self.title_file(title_key).parsed(), season_keys)

    # TODO: Validate
    @staticmethod
    def is_clip_season(season: SeasonData) -> bool:
        return season.type == "CLIP"

    # TODO: Validate
    @classmethod
    def season_key(cls, season: SeasonData) -> str:
        if cls.is_clip_season(season):
            return f"clip-{season.number}"
        return str(season.number)

    # TODO: Validate
    @classmethod
    def season_keys(cls, title: ShowModel) -> list[str]:
        return [cls.season_key(season) for season in title.seasons]

    # TODO: Validate
    @classmethod
    def episode_keys(cls, title: ShowModel, wanted_season_keys: list[str]) -> list[str]:
        return [
            episode.id
            for season in title.seasons
            if cls.season_key(season) in wanted_season_keys
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def validate_url(self, url: str) -> None:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_file = self.title_file(title_key)
            self.raise_invalid_url_if_no_content(title_file, url)
            if self.episode_key_from_slug(title_file.parsed(), episode_slug):
                return

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            self.raise_invalid_url_if_no_content(
                self.title_file(match.group("title_key")),
                url,
            )
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_data = self.title_file(title_key).parsed()
            if episode_key := self.episode_key_from_slug(title_data, episode_slug):
                return ParsedURL(title_key, episode_key=episode_key)

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            return ParsedURL(match.group("title_key"))

        # Should be impossible
        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        if not (titles := self._preload_title(media_info.title_key).all()):
            self._preload_and_download_files(media_info.title_key)
            titles = [
                self._upsert_title(source, media_info.title_key)
                for source in self._sources.values()
            ]
            for title in titles:
                self.add_title_to_channels(title)
        return [
            result
            for title in titles
            for result in self._import_results(title, media_info)
        ]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        title_data = self.title_file(title_key).parsed()
        metadata = title_data.metadata
        hero = title_data.hero
        existing_title = Title.get_from_memory(self.session, source, title_key)
        upserted_title = Title(
            key=title_key,
            name=title_data.title,
            description=metadata.description if metadata else None,
            media_type=MediaType.series,
            url=self.title_url(title_key),
            image_url=hero.image_url,
            thumbnail_url=metadata.thumbnail if metadata else None,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )

        self._upsert_seasons(
            upserted_title,
            title_data,
            source_key=source.key,
        )
        self._soft_delete_missing(upserted_title, title_data, source_key=source.key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _soft_delete_missing(
        self,
        title: Title,
        title_data: ShowModel,
        *,
        source_key: str,
    ) -> None:
        episode_keys_by_season = {
            self.season_key(season_data): [
                episode_data.id
                for episode_data in self.source_episodes(season_data, source_key)
            ]
            for season_data in title_data.seasons
        }
        title.soft_delete_missing_children(episode_keys_by_season)
        for season in title.seasons:
            if season.key in episode_keys_by_season:
                season.soft_delete_missing_children(episode_keys_by_season[season.key])

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_data: ShowModel,
        *,
        source_key: str,
    ) -> None:
        for sort_order, season_data in enumerate(title_data.seasons):
            key = self.season_key(season_data)
            existing_season = Season.get_from_memory(self.session, title, key)
            upserted_season = Season(
                key=key,
                name=self.season_name(season_data),
                season_number=(
                    0 if self.is_clip_season(season_data) else season_data.number
                ),
                sort_order=(
                    2147483647 if self.is_clip_season(season_data) else sort_order
                ),
                data_timestamp=self._season_files_data_timestamp(
                    key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(
                upserted_season,
                title.key,
                season_data,
                source_key=source_key,
            )
            self._set_season_update_at(upserted_season)
            for episode_data in self.source_episodes(season_data, source_key):
                if episode_data.expiration_date:
                    upserted_season.set_update_at(episode_data.expiration_date)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_data: SeasonData,
        *,
        source_key: str,
    ) -> None:
        episodes_data = self.source_episodes(season_data, source_key)
        for sort_order, episode_data in enumerate(episodes_data):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_data.id,
            )
            Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(
                    self.plugin_name(),
                    episode_data.id,
                ),
                name=episode_data.title,
                description=episode_data.description,
                url=self.episode_url(
                    episode_data.collection_slug,
                    episode_data.slug,
                ),
                image_url=episode_data.poster,
                thumbnail_url=episode_data.poster,
                air_date=self.episode_air_date(episode_data),
                duration=int(episode_data.duration),
                episode_number=episode_data.episode_number,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_data.id,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

    # TODO: Validate
    @classmethod
    def episode_url(cls, title_key: str, episode_slug: str) -> str:
        return cls.build_url(f"videos/{title_key}/{episode_slug}")

    # TODO: Validate
    @staticmethod
    def source_requires_auth(source_key: str) -> bool:
        return source_key == SUBSCRIPTION

    # TODO: Validate
    @classmethod
    def season_name(cls, season: SeasonData) -> str:
        if cls.is_clip_season(season):
            return f"Clips from Season {season.number}"
        return season.name

    # TODO: Validate
    @classmethod
    def source_episodes(cls, season: SeasonData, source_key: str) -> list[EpisodeData]:
        return [
            episode_data
            for episode_data in season.episodes
            if episode_data.auth == cls.source_requires_auth(source_key)
        ]

    # TODO: Validate
    @staticmethod
    def episode_air_date(episode: EpisodeData) -> datetime | None:
        air_date = episode.first_airing or episode.launch_date
        if isinstance(air_date, str):
            return datetime.fromisoformat(air_date)
        return air_date

    # TODO: Validate
    @staticmethod
    def episode_key_from_slug(title: ShowModel, episode_slug: str) -> str | None:
        for season in title.seasons:
            for episode in season.episodes:
                if episode.slug == episode_slug:
                    return episode.id
        return None


# TODO: Validate
class AdultSwimSeriesImporter(AdultSwimSeriesUpsert):
    pass
