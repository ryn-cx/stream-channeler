# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from loguru import logger

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.utils import tz_datetime
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
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.plugins.models import Plugin
    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AdultSwim(
    AdultSwimShared,
    BaseImporter,
    AbstractPlugin,
    register=False,
):
    # TODO: Validate
    @override
    def _create_initial_source_records(self) -> None:
        super()._create_initial_source_records()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()

    # TODO: Validate
    @override
    def _create_initial_channel_records(self) -> None:
        self._channels()
        self._process_new_titles()

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def update_plugin(self, plugin: Plugin) -> None:
        logger.info("Checking Adult Swim for new titles")
        self.titles_file().download_if_outdated(tz_datetime.now())
        self._process_new_titles()
        self._exclude_subscription_from_free_channel()
        plugin.update_at = tz_datetime.now() + self._next_update_interval()

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_file = self.title_file(title_key)
            self.raise_invalid_url_if_no_content(title_file, url)
            episode_key = episode_key_for_slug(title_file.parsed(), episode_slug)
            if episode_key is None:
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return ParsedURL(title_key, episode_key=episode_key)

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.title_file(title_key), url)
            return ParsedURL(title_key)

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
        media_info = self.parse_url(url)
        titles = list(self._preload_title(media_info.title_key))
        if not titles:
            self._preload_and_download_files(media_info.title_key)
            titles = [
                self._upsert_title(source, media_info.title_key)
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
    def _upsert_title(
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
            title = Title(
                key=title_key,
                name=title_data.title,
                description=metadata.description if metadata else None,
                media_type="Series",
                url=title_url(title_key),
                image_url=hero.image_url if hero else None,
                thumbnail_url=metadata.thumbnail if metadata else None,
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_seasons(
            title,
            title_data,
            requires_auth=source_requires_auth(source.key),
            force=force,
        )
        self._soft_delete_missing_seasons_and_episodes(title_key)

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
                season = Season(
                    key=season_key,
                    name=season_data.name,
                    season_number=season_data.number,
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
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
                    key=episode_data.id,
                    watch_identifier=watch_identifier(
                        self.plugin_name(),
                        episode_data.id,
                    ),
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
                    data_timestamp=self._episode_files_data_timestamp(
                        episode_data.id,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(None)

        season.soft_delete_missing_children(
            episode_data.id for episode_data in episodes_data
        )
