# TODO: Validate
"""Writing what Tubi says about a series into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Tubi.constants import EPISODE_URL_REGEX, SERIES_URL_REGEX
from plugins.Tubi.shared import (
    TubiImporter,
    TubiShared,
    build_season_key,
    episode_name,
    episode_url,
    first_image,
    season_episodes,
    seasons,
    series_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from plugi.content.models import Child as SeasonChild
    from plugi.content.models import Child1 as EpisodeChild

    from app.sources.models import Source


# TODO: Validate
class TubiSeriesFiles(TubiShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    def _seasons(self, title_key: str) -> list[SeasonChild]:
        return seasons(self._content(title_key))

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_id: str) -> list[EpisodeChild]:
        return season_episodes(self._content(title_key), season_id)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            build_season_key(title_key, season.id)
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
            _title_key, season_id = split_season_key(season_key)
            episode_keys += [
                episode.id for episode in self._season_episodes(title_key, season_id)
            ]
        return episode_keys


# TODO: Validate
class TubiSeriesUpsert(TubiSeriesFiles, TubiImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.content_file(title_key), url)
            return ParsedURL(title_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_key")
            self.raise_invalid_url_if_no_content(self.content_file(episode_key), url)
            series_id = self._content(episode_key).series_id
            if series_id is None:
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return ParsedURL(series_id, episode_key=episode_key)

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
        content = self._content(title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=content.title,
            description=content.description,
            media_type=MediaType.series,
            year=content.year,
            url=series_url(title_key),
            image_url=first_image(content.backgrounds),
            thumbnail_url=first_image(content.backgrounds),
            poster_url=first_image(content.posterarts),
            poster_thumbnail_url=first_image(content.posterarts),
            data_timestamp=data_timestamp,
            source_id=source.id,
            update_at=data_timestamp + timedelta(days=7),
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(content.tags)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_content in enumerate(self._seasons(title.key)):
            season_key = build_season_key(title.key, season_content.id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=season_content.title,
                season_number=int(season_content.id),
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(
                upserted_season,
                title.key,
                season_content.id,
            )
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_id: str,
    ) -> None:
        for sort_order, episode_content in enumerate(
            self._season_episodes(title_key, season_id),
        ):
            episode_key = episode_content.id
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=episode_name(episode_content.title),
                description=episode_content.description,
                episode_number=int(episode_content.episode_number),
                url=episode_url(episode_key),
                image_url=first_image(episode_content.thumbnails),
                thumbnail_url=first_image(episode_content.thumbnails),
                duration=episode_content.duration,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class TubiSeriesImporter(TubiSeriesUpsert):
    pass
