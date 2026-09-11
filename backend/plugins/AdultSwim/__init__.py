# TODO: Validate
from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.AdultSwim.constants import EPISODE_URL_REGEX, TITLE_URL_REGEX
from plugins.AdultSwim.shared import AdultSwimShared
from plugins.AdultSwim.utils import (
    episode_key_from_slug,
    episode_url,
    season_key,
    season_name,
    source_episodes,
    source_requires_auth,
    title_url,
)
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from datetime import datetime

    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class AdultSwim(
    AdultSwimShared,
    BaseImporter,
    AbstractPlugin,
    register=True,
):
    # TODO: Validate
    @override
    def _next_plugin_update_at(self) -> datetime:
        return max(self._plugin_files_data_timestamps()) + timedelta(days=7)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def validate_url(self, url: str) -> None:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_file = self.title_file(title_key)
            self.raise_invalid_url_if_no_content(title_file, url)
            if episode_key_from_slug(title_file.parsed(), episode_slug):
                return

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            self.raise_invalid_url_if_no_content(
                self.title_file(match.group("title_key")),
                url,
            )
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            title_key, episode_slug = match.group("episode_path").split("/")
            title_data = self.title_file(title_key).parsed()
            if episode_key := episode_key_from_slug(title_data, episode_slug):
                return ParsedURL(title_key, episode_key=episode_key)

        if match := re.match(domain_regex + TITLE_URL_REGEX, url):
            return ParsedURL(match.group("title_key"))

        # Should be impossible
        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        if not (titles := self._preload_title(media_info.title_key).all()):
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
                image_url=hero.image_url,
                thumbnail_url=metadata.thumbnail if metadata else None,
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        requires_auth = source_requires_auth(source.key)
        self._upsert_seasons(
            title,
            title_data,
            requires_auth=requires_auth,
            force=force,
        )
        self._soft_delete_missing(title, title_data, requires_auth=requires_auth)

        return title

    # TODO: Validate
    def _soft_delete_missing(
        self,
        title: Title,
        title_data: ShowModel,
        *,
        requires_auth: bool,
    ) -> None:
        episode_keys_by_season = {
            season_key(season_data): [
                episode_data.id
                for episode_data in source_episodes(
                    season_data,
                    requires_auth=requires_auth,
                )
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
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        for sort_order, season_data in enumerate(title_data.seasons):
            key = season_key(season_data)
            season = Season.get_from_memory(self.session, title, key)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=key,
                    name=season_name(season_data),
                    season_number=season_data.number,
                    sort_order=sort_order,
                    data_timestamp=self._season_files_data_timestamp(
                        key,
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
        episodes_data = source_episodes(season_data, requires_auth=requires_auth)
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
