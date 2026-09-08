# TODO: Validate
"""Writing what Adult Swim says about a title into the database."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from plugins.AdultSwim.constants import EPISODE_URL_REGEX, TITLE_URL_REGEX
from plugins.AdultSwim.shared import AdultSwimShared
from plugins.AdultSwim.utils import (
    episode_key_for_slug,
    episode_keys,
    episode_url,
    season_keys,
    source_requires_auth,
    title_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AdultSwimImporter(AdultSwimShared, BaseImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        domain_regex = self._domain_regex()

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_file = self.title_file(title_key)
            self.raise_if_invalid_file(title_file, url)
            episode_key = episode_key_for_slug(title_file.parsed(), episode_slug)
            if episode_key is None:
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return URLTitleInfo(title_key, episode_key=episode_key)

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_if_invalid_file(self.title_file(title_key), url)
            return URLTitleInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        """Import the title into every source Adult Swim is offered through.

        The free listing and the subscription one hold different episodes of the
        same title, so an address names a title on both and each of them is
        written.
        """
        media_info = self.get_media_info(url)
        titles = list(self._preload_title(media_info.title_key))
        if not titles:
            titles = [
                self.upsert_title(source, media_info.title_key)
                for source in self._sources.values()
            ]
        return [
            result
            for title in titles
            for result in self._import_results(title, media_info)
        ]

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
        return season_keys(self.title_file(title_key).parsed())

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return episode_keys(self.title_file(title_key).parsed(), season_keys)

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title_data = self.title_file(title_key).parsed()
        metadata = title_data.metadata
        hero = title_data.hero
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=title_data.title,
                description=metadata.description if metadata else None,
                media_type="Series",
                url=title_url(title_key),
                image_url=hero.image_url if hero else None,
                thumbnail_url=metadata.thumbnail if metadata else None,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_seasons(
            title,
            title_data,
            requires_auth=source_requires_auth(source.key),
            force=force,
        )
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_data: ShowModel,
        *,
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        for sort_order, season_data in enumerate(title_data.seasons):
            season_key = str(season_data.number)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                season = Season(
                    key=season_key,
                    name=season_data.name,
                    season_number=season_data.number,
                    sort_order=sort_order,
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(
                season,
                title.key,
                season_data,
                requires_auth=requires_auth,
                force=force,
            )
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_data: SeasonData,
        *,
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        episodes_data = [
            episode_data
            for episode_data in season_data.episodes
            if episode_data.auth == requires_auth
        ]
        for sort_order, episode_data in enumerate(episodes_data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_data.id,
                season.key,
                title_key,
            )
            episode = Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(self.plugin_name(), episode_data.id),
                name=episode_data.title,
                description=episode_data.description,
                url=episode_url(
                    episode_data.collection_slug,
                    episode_data.slug,
                ),
                image_url=episode_data.poster,
                thumbnail_url=episode_data.poster,
                air_date=episode_data.first_airing or episode_data.launch_date,
                duration=int(episode_data.duration),
                episode_number=episode_data.episode_number,
                sort_order=sort_order,
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)

        season.soft_delete_missing_children(
            episode_data.id for episode_data in episodes_data
        )
