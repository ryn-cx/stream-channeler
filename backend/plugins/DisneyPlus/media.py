# TODO: Validate
"""Writing what Disney+ says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.DisneyPlus.shared import ENTITY_URL_REGEX, DisneyPlusShared
from plugins.DisneyPlus.utils import (
    background_image_url,
    build_season_key,
    media_details,
    release_year,
    required_value,
    season_episodes,
    season_number_from_name,
    seasons,
    show_url,
    split_season_key,
    video_url,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kneeminus.entity.models import EntityModel, MainContentItem
    from kneeminus.entity.models import Episode as EntityEpisode
    from kneeminus.entity.models import Season as EntitySeason

    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class DisneyPlusMedia(DisneyPlusShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + ENTITY_URL_REGEX, url):
            show_key = match.group("entity_key")
            self.raise_if_invalid_file(self.entity_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _entity(self, show_key: str) -> EntityModel:
        return self.entity_file(show_key).parsed()

    # TODO: Validate
    def _media_details(self, show_key: str) -> MainContentItem:
        return media_details(self._entity(show_key))

    # TODO: Validate
    def _background_image_url(self, show_key: str) -> str:
        return background_image_url(self._entity(show_key))

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.entity_file(show_key)]

    # TODO: Validate
    def _tmdb_lookup_info(
        self,
        show_key: str,
        media_type: TMDBMediaType,
    ) -> list[TMDBLookupInfo]:
        self.entity_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        return [
            TMDBLookupInfo(
                required_value(self._media_details(show_key).title, "title"),
                media_type,
                release_year(self._entity(show_key)),
            ),
        ]


# TODO: Validate
class DisneyPlusSeries(DisneyPlusMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.tv)

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[EntitySeason]:
        return seasons(self._entity(show_key))

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_id: str) -> list[EntityEpisode]:
        return season_episodes(self.season_file(show_key, season_id).parsed())

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _show_key, season_id = split_season_key(season_key)
        return [self.season_file(show_key, season_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return self._season_files(season_key, show_key)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, str(season.id))
            for season in self._seasons(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            _show_key, season_id = split_season_key(season_key)
            episode_keys += [
                str(episode.field_id)
                for episode in self._season_episodes(show_key, season_id)
            ]
        return episode_keys

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            details = self._media_details(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="Series",
                url=show_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
                year=release_year(self._entity(show_key)),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                staggered_monthly_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_entry in enumerate(self._seasons(show.key)):
            season_id = str(season_entry.id)
            season_key = build_season_key(show.key, season_id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_number_from_name(
                        season_entry.name,
                        sort_order + 1,
                    ),
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, show.key, season_id, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self._season_episodes(show_key, season_id)):
            episode_key = str(item.field_id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                show_key,
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
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class DisneyPlusMovie(DisneyPlusMedia):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.movie)

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # A movie is a season of itself, so its own page is what it is read out of.
        return [self.entity_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.entity_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [build_season_key(show_key, show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        details = self._media_details(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=required_value(details.title, "title"),
                description=details.summary,
                media_type="Movie",
                url=show_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
                year=release_year(self._entity(show_key)),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                staggered_monthly_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(self, show: Show, *, force: bool = False) -> None:
        season_key = build_season_key(show.key, show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, show.key)
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            details = self._media_details(show_key)
            data_timestamps = self.episode_data_timestamps(
                show_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=show_key,
                watch_identifier=watch_identifier(self.plugin_name(), show_key),
                name=required_value(details.title, "title"),
                description=details.summary,
                url=video_url(show_key),
                image_url=self._background_image_url(show_key),
                thumbnail_url=self._background_image_url(show_key),
                episode_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
