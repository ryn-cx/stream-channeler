# TODO: Validate
"""Writing what Disney+ says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.utils.update_at import staggered_monthly_update_at
from plugins.DisneyPlus.constants import ENTITY_URL_REGEX
from plugins.DisneyPlus.shared import DisneyPlusShared
from plugins.DisneyPlus.utils import (
    background_image_url,
    build_season_key,
    media_details,
    release_year,
    required_value,
    season_episodes,
    season_number_from_name,
    seasons,
    split_season_key,
    title_url,
    video_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kneeminus.entity.models import EntityModel, MainContentItem
    from kneeminus.entity.models import Episode as EntityEpisode
    from kneeminus.entity.models import Season as EntitySeason

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class DisneyPlusImporter(DisneyPlusShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        if match := re.match(self._domain_regex() + ENTITY_URL_REGEX, url):
            title_key = match.group("entity_key")
            self.raise_if_invalid_file(self.entity_file(title_key), url)
            return URLTitleInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _entity(self, title_key: str) -> EntityModel:
        return self.entity_file(title_key).parsed()

    # TODO: Validate
    def _media_details(self, title_key: str) -> MainContentItem:
        return media_details(self._entity(title_key))

    # TODO: Validate
    def _background_image_url(self, title_key: str) -> str:
        return background_image_url(self._entity(title_key))

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.entity_file(title_key)]


# TODO: Validate
class DisneyPlusSeriesImporter(DisneyPlusImporter):
    # TODO: Validate
    def _seasons(self, title_key: str) -> list[EntitySeason]:
        return seasons(self._entity(title_key))

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_id: str) -> list[EntityEpisode]:
        return season_episodes(self.season_file(title_key, season_id).parsed())

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_id = split_season_key(season_key)
        return [self.season_file(title_key, season_id)]

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
            build_season_key(title_key, str(season.id))
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
                str(episode.field_id)
                for episode in self._season_episodes(title_key, season_id)
            ]
        return episode_keys

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            details = self._media_details(title_key)
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="Series",
                url=title_url(title_key),
                image_url=self._background_image_url(title_key),
                thumbnail_url=self._background_image_url(title_key),
                year=release_year(self._entity(title_key)),
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
                data_timestamps,
            )

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_entry in enumerate(self._seasons(title.key)):
            season_id = str(season_entry.id)
            season_key = build_season_key(title.key, season_id)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_number_from_name(
                        season_entry.name,
                        sort_order + 1,
                    ),
                    sort_order=sort_order,
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, title.key, season_id, force=force)
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
        for sort_order, item in enumerate(self._season_episodes(title_key, season_id)):
            episode_key = str(item.field_id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                title_key,
            )
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.title,
                episode_number=sort_order + 1,
                url=video_url(episode_key),
                description=item.metadata.summary,
                image_url=item.image_variants.default_image.source,
                thumbnail_url=item.image_variants.default_image.source,
                sort_order=sort_order,
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class DisneyPlusMovieImporter(DisneyPlusImporter):
    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # A movie is a season of itself, so its own page is what it is read out of.
        return [self.entity_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.entity_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [build_season_key(title_key, title_key)]

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
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        details = self._media_details(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="Movie",
                url=title_url(title_key),
                image_url=self._background_image_url(title_key),
                thumbnail_url=self._background_image_url(title_key),
                year=release_year(self._entity(title_key)),
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
                data_timestamps,
            )

        self._upsert_season(title, force=force)
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season_key = build_season_key(title.key, title.key)
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title.key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, title.key)
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            )
            season = new_season.upsert(title, season)
            season.set_update_at(None, data_timestamps)

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
        if self._episode_is_outdated(episode, season.key, title_key, force=force):
            details = self._media_details(title_key)
            data_timestamps = self.episode_data_timestamps(
                title_key,
                season.key,
                title_key,
            )
            new_episode = Episode(
                key=title_key,
                watch_identifier=watch_identifier(self.plugin_name(), title_key),
                name=required_value(details.title, "title"),
                description=details.summary,
                url=video_url(title_key),
                image_url=self._background_image_url(title_key),
                thumbnail_url=self._background_image_url(title_key),
                episode_number=0,
                sort_order=0,
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
