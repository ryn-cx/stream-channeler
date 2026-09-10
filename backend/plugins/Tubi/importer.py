# TODO: Validate
"""Writing what Tubi says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.utils.update_at import staggered_monthly_update_at
from plugins.Tubi.constants import EPISODE_URL_REGEX, MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Tubi.shared import TubiShared
from plugins.Tubi.utils import (
    build_season_key,
    episode_name,
    episode_url,
    first_image,
    movie_season_key,
    movie_url,
    season_episodes,
    seasons,
    series_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugi.content.models import Child as SeasonChild
    from plugi.content.models import Child1 as EpisodeChild
    from plugi.content.models import ContentModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class TubiImporter(TubiShared, BaseImporter, ABC):
    # TODO: Validate
    def _content(self, title_key: str) -> ContentModel:
        return self.content_file(title_key).parsed()

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the title's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]


# TODO: Validate
class TubiSeriesImporter(TubiImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("series_key")
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
            content = self._content(title_key)
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=content.title,
                description=content.description,
                media_type="Series",
                year=content.year,
                url=series_url(title_key),
                image_url=first_image(content.backgrounds),
                thumbnail_url=first_image(content.backgrounds),
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(min(data_timestamps) + timedelta(days=7))

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_content in enumerate(self._seasons(title.key)):
            season_key = build_season_key(title.key, season_content.id)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=season_key,
                    name=season_content.title,
                    season_number=int(season_content.id),
                    sort_order=sort_order,
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(
                season,
                title.key,
                season_content.id,
                force=force,
            )
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_content in enumerate(
            self._season_episodes(title_key, season_id),
        ):
            episode_key = episode_content.id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
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
                ).upsert(season, episode)
                episode.set_update_at(None)


# TODO: Validate
class TubiMovieImporter(TubiImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("movie_key")
            self.raise_invalid_url_if_no_content(self.content_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [movie_season_key(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        content = self._content(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                year=content.year,
                url=movie_url(title_key),
                image_url=first_image(content.backgrounds),
                thumbnail_url=first_image(content.backgrounds),
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
            )

        self._upsert_season(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season_key = movie_season_key(title.key)
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title.key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(season_key, title.key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

        self._upsert_episode(season, title.key, force=force)
        self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if self._episode_is_outdated(
            episode,
            season.key,
            title_key,
            force=force,
        ):
            content = self._content(title_key)
            episode = Episode(
                key=title_key,
                watch_identifier=watch_identifier(self.plugin_name(), title_key),
                name=content.title,
                description=content.description,
                episode_number=0,
                url=movie_url(title_key),
                image_url=first_image(content.backgrounds),
                thumbnail_url=first_image(content.backgrounds),
                duration=content.duration,
                sort_order=0,
                data_timestamp=self._episode_files_data_timestamp(
                    title_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)
