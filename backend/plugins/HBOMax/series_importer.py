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
from plugins.HBOMax.shared import (
    HBOMaxImporter,
    HBOMaxShared,
    build_episode_key,
    build_season_key,
    page_urls,
    related_urls,
    season_entry,
    season_episodes,
    season_numbers,
    split_season_key,
    title_content,
    title_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from minbo.show.models import Idref14 as TitleContent

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HBOMaxSeriesFiles(HBOMaxShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    def _title_content(self, title_key: str) -> TitleContent:
        return title_content(self.title_file(title_key).parsed())

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = split_season_key(season_key)
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
            build_season_key(title_key, season_number)
            for season_number in season_numbers(self.title_file(title_key).parsed())
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
            _title_key, season_number = split_season_key(season_key)
            episode_keys += [
                build_episode_key(season_key, episode.episode_number)
                for episode in self._season_episodes(title_key, season_number)
            ]
        return episode_keys

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_number: int) -> list[Any]:
        return season_episodes(
            self.season_file(title_key, season_number).parsed(),
            season_number,
        )


# TODO: Validate
class HBOMaxSeriesUpsert(HBOMaxSeriesFiles, HBOMaxImporter, ABC):
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
        urls = [title.url, *page_urls(page)]
        self.add_new_urls_to_channel("All Titles", urls)
        for channel_key in ["Series", *title_content(page).genres]:
            self.add_new_urls_to_channel(channel_key, [title.url])

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return related_urls(self.title_file(title.key).parsed())

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
            name=content.title.full,
            description=content.summary.full,
            media_type=MediaType.series,
            url=title_url(title_key),
            year=int(content.release_year),
            image_url=content.image_url_link,
            thumbnail_url=content.image_url_link,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(content.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        title_file = self.title_file(title.key)
        for sort_order, season_number in enumerate(season_numbers(title_file.parsed())):
            season_key = build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            entry = season_entry(title_file.parsed(), season_number)
            upserted_season = Season(
                key=season_key,
                name=entry.title.full,
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
            episode_key = build_episode_key(season.key, item.episode_number)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=str(item.title.full),
                episode_number=item.episode_number,
                url=item.episode_url,
                description=item.summary.full,
                image_url=item.images.default,
                thumbnail_url=item.images.default,
                air_date=item.offering_dates.start_date,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate


# TODO: Validate
class HBOMaxSeriesImporter(HBOMaxSeriesUpsert):
    pass
