# TODO: Validate
"""Writing what Adult Swim says about a title into the database."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from plugins.AdultSwim.shared import (
    EPISODE_URL_REGEX,
    SHOW_URL_REGEX,
    AdultSwimShared,
)
from plugins.AdultSwim.utils import (
    episode_key_for_slug,
    episode_keys,
    episode_url,
    season_keys,
    show_url,
    source_requires_auth,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class AdultSwimMedia(AdultSwimShared, BaseImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (EPISODE_URL_REGEX, SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            show_key, episode_slug = match.group("episode_path").split("/")
            show_file = self.show_file(show_key)
            self.raise_if_invalid_file(show_file, url)
            episode_key = episode_key_for_slug(show_file.parsed(), episode_slug)
            if episode_key is None:
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return MediaInfo(show_key, episode_key=episode_key)

        if match := re.match(domain_regex + SHOW_URL_REGEX, url):
            show_key = match.group("show_key")
            self.raise_if_invalid_file(self.show_file(show_key), url)
            return MediaInfo(show_key)

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
        media_info = self.extract_media_info(url)
        shows = list(self._preload_show(media_info.show_key))
        if not shows:
            shows = [
                self.upsert_show(source, media_info.show_key)
                for source in self._sources.values()
            ]
        return [
            result
            for show in shows
            for result in self._import_results(show, media_info)
        ]

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        show_page = self.show_file(show_key)
        return [TMDBLookupInfo(show_page.parsed().title, TMDBMediaType.tv, None)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return season_keys(self.show_file(show_key).parsed())

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return episode_keys(self.show_file(show_key).parsed(), season_keys)

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show_data = self.show_file(show_key).parsed()
        metadata = show_data.metadata
        hero = show_data.hero
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=show_key,
                name=show_data.title,
                description=metadata.description if metadata else None,
                media_type="Series",
                url=show_url(show_key),
                image_url=hero.image_url if hero else None,
                thumbnail_url=metadata.thumbnail if metadata else None,
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons(
            show,
            show_data,
            requires_auth=source_requires_auth(source.key),
            force=force,
        )
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        show_data: ShowModel,
        *,
        requires_auth: bool,
        force: bool = False,
    ) -> None:
        for sort_order, season_data in enumerate(show_data.seasons):
            season_key = str(season_data.number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=season_data.name,
                    season_number=season_data.number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(
                season,
                show.key,
                season_data,
                requires_auth=requires_auth,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
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
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_data.id,
                season.key,
                show_key,
            )
            new_episode = Episode(
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
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)

        season.soft_delete_missing_children(
            episode_data.id for episode_data in episodes_data
        )
