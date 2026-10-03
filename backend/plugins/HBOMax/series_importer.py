# TODO: Validate
"""Writing what HBO Max says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.HBOMax.constants import TITLE_URL_REGEX
from plugins.HBOMax.files import SeasonFile, TitleFile
from plugins.HBOMax.shared import HBOMaxImporter
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from minbo.show.models import Episode as ParsedEpisode
    from minbo.show.models import ParsedShowModel
    from minbo.show.models import Season as ParsedSeason

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HBOMaxSeriesFiles(HBOMaxImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    def title_file(self, title_id: str) -> TitleFile:
        return self._cached_file(TitleFile, title_id)

    # TODO: Validate
    def season_file(self, title_id: str, season_number: int) -> SeasonFile:
        return self._cached_file(SeasonFile, title_id, season_number)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = self.split_season_key(season_key)
        # Required to detect changes to the season and new episodes of it.
        return [self.season_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return self._season_files(season_key, title_key)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            self.build_season_key(title_key, season_number)
            for season_number in self.season_numbers(
                self.title_file(title_key).parsed(),
            )
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
            _title_key, season_number = self.split_season_key(season_key)
            episode_keys += [
                self.build_episode_key(season_key, episode.episode_number)
                for episode in self._season_episodes(title_key, season_number)
            ]
        return episode_keys

    # TODO: Validate
    def _season_episodes(
        self,
        title_key: str,
        season_number: int,
    ) -> list[ParsedEpisode]:
        return self.season_episodes(
            self.season_file(title_key, season_number).parsed(),
            season_number,
        )

    # TODO: Validate
    @staticmethod
    def build_episode_key(season_key: str, episode_number: int) -> str:
        return f"{season_key}:{episode_number}"

    # TODO: Validate
    @staticmethod
    def season_numbers(title: ParsedShowModel) -> list[int]:
        return [season.season_number for season in title.seasons]

    # TODO: Validate
    @staticmethod
    def season_entry(title: ParsedShowModel, season_number: int) -> ParsedSeason:
        for season in title.seasons:
            if season.season_number == season_number:
                return season
        msg = f"Season {season_number} not found."
        raise ValueError(msg)

    # TODO: Validate
    @classmethod
    def season_episodes(
        cls,
        season: ParsedShowModel,
        season_number: int,
    ) -> list[ParsedEpisode]:
        return cls.season_entry(season, season_number).episodes


# TODO: Validate
class HBOMaxSeriesUpsert(HBOMaxSeriesFiles, ABC):
    # TODO: Validate
    def _title_content(self, title_key: str) -> ParsedShowModel:
        return self.title_file(title_key).parsed()

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.title_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        page = self.title_file(title.key).parsed()
        self.add_title_to_channel("All Titles", title)
        self.add_new_urls_to_channel("All Titles", self.page_urls(page))
        self.set_title_tag_channels(title, ["Series", *page.genres])

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self.related_urls(self.title_file(title.key).parsed())

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        content = self._title_content(title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=content.title,
            description=content.summary,
            media_type=MediaType.series,
            url=content.url,
            year=content.release_year,
            image_url=content.images.default_wide or content.images.default,
            thumbnail_url=content.images.default_wide or content.images.default,
            poster_url=content.images.cover_artwork,
            poster_thumbnail_url=content.images.cover_artwork,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(content.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        upserted_title.set_update_at(content.end_date)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        title_file = self.title_file(title.key)
        for sort_order, season_number in enumerate(
            self.season_numbers(title_file.parsed()),
        ):
            season_key = self.build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            entry = self.season_entry(title_file.parsed(), season_number)
            upserted_season = Season(
                key=season_key,
                name=entry.name,
                season_number=season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, season_number)
            self._set_season_update_at(upserted_season)
            for item in self._season_episodes(title.key, season_number):
                upserted_season.set_update_at(item.end_date)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = self.build_episode_key(season.key, item.episode_number)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.title,
                episode_number=item.episode_number,
                url=item.url,
                description=item.summary,
                image_url=item.images.default_wide or item.images.default,
                thumbnail_url=item.images.default_wide or item.images.default,
                air_date=item.start_date,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class HBOMaxSeriesImporter(HBOMaxSeriesUpsert):
    pass
