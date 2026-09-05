# TODO: Validate
"""Writing what HBO Max says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils.update_at import staggered_monthly_update_at
from plugins.HBOMax.shared import MOVIE_URL_REGEX, SHOW_URL_REGEX, HBOMaxShared
from plugins.HBOMax.utils import (
    build_episode_key,
    build_season_key,
    movie_content,
    movie_url,
    season_entry,
    season_episodes,
    season_numbers,
    show_content,
    show_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from minbo.movie.models import Idref14 as MovieContent
    from minbo.show.models import Idref14 as ShowContent

    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class HBOMaxMedia(HBOMaxShared, BaseImporter, ABC):
    pass


# TODO: Validate
class HBOMaxSeries(HBOMaxMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SHOW_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + SHOW_URL_REGEX, url):
            show_key = match.group("show_key")
            self.raise_if_invalid_file(self.show_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _show_content(self, show_key: str) -> ShowContent:
        return show_content(self.show_file(show_key).parsed())

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        content = self._show_content(show_key)
        return [
            TMDBLookupInfo(
                content.title.full,
                TMDBMediaType.tv,
                int(content.release_year),
            ),
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _show_key, season_number = split_season_key(season_key)
        # Required to detect changes to the season and new episodes of it.
        return [self.season_file(show_key, season_number)]

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
            build_season_key(show_key, season_number)
            for season_number in season_numbers(self.show_file(show_key).parsed())
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
            _show_key, season_number = split_season_key(season_key)
            episode_keys += [
                build_episode_key(season_key, episode.episode_number)
                for episode in self._season_episodes(show_key, season_number)
            ]
        return episode_keys

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_number: int) -> list[Any]:
        return season_episodes(
            self.season_file(show_key, season_number).parsed(),
            season_number,
        )

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
            content = self._show_content(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="Series",
                url=show_url(show_key),
                image_url=content.image_url_link,
                thumbnail_url=content.image_url_link,
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
        show_file = self.show_file(show.key)
        for sort_order, season_number in enumerate(season_numbers(show_file.parsed())):
            season_key = build_season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                entry = season_entry(show_file.parsed(), season_number)
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=entry.title.full,
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, show.key, season_number, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(show_key, season_number),
        ):
            episode_key = build_episode_key(season.key, item.episode_number)
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
                name=str(item.title.full),
                episode_number=item.episode_number,
                url=item.episode_url,
                description=item.summary.full,
                image_url=item.images.default,
                thumbnail_url=item.images.default,
                air_date=item.offering_dates.start_date,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class HBOMaxMovie(HBOMaxMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + MOVIE_URL_REGEX, url):
            show_key = match.group("movie_key")
            self.raise_if_invalid_file(self.movie_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _movie_content(self, show_key: str) -> MovieContent:
        return movie_content(self.movie_file(show_key).parsed())

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        content = self._movie_content(show_key)
        return [
            TMDBLookupInfo(
                content.title.full,
                TMDBMediaType.movie,
                int(content.release_year),
            ),
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [build_season_key(show_key, 0)]

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
        content = self._movie_content(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title.full,
                description=content.summary.full,
                media_type="Movie",
                url=movie_url(show_key),
                image_url=content.image_url_link,
                thumbnail_url=content.image_url_link,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                staggered_monthly_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(show, content, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        content: MovieContent,
        *,
        force: bool = False,
    ) -> None:
        season_key = build_season_key(show.key, 0)
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

        self._upsert_episode(season, show.key, content, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        content: MovieContent,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            data_timestamps = self.episode_data_timestamps(
                show_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=show_key,
                watch_identifier=watch_identifier(self.plugin_name(), show_key),
                name=content.title.full,
                description=content.summary.full,
                url=movie_url(show_key),
                image_url=content.image_url_link,
                thumbnail_url=content.image_url_link,
                episode_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
