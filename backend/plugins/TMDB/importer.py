# TODO: Validate
"""Reading a TMDB title as the half of the catalogue it belongs to."""

from __future__ import annotations

import re
from abc import abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from random import Random
from typing import Any, override

from app.canonical_media.keys import (
    watch_identifier,
)
from app.canonical_media.tmdb import (
    chosen_group_id,
    dump_episode_extra,
    get_media_type_and_episode_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_title_key,
)
from app.episodes.models import Episode
from app.episodes.preload import preload_episodes
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from app.utils.update_at import title_update_at
from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.external_websites import TMDBExternalWebsites
from plugins.TMDB.files import (
    MoviesWatchProviders,
    TVSeasonsChanges,
    TVSeriesChanges,
    TVSeriesWatchProviders,
)
from plugins.TMDB.utils import (
    TMDBSeasonInfo,
    image_url,
    parse_release_year,
    thumbnail_url,
    tmdb_url,
)
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.files import (
    BaseFile,
)
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo


# TODO: Validate
def clean_air_datetime(air_date: str | date | None) -> datetime | None:
    """Return a datetime for the air date and replaces empty strings with None.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if not isinstance(air_date, date):
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
def runtime_in_seconds(runtime: int | None) -> int | None:
    # If the runtime is not known the API returns None. In all other cases it returns
    # the runtime in minutes.
    return runtime * 60 if runtime else None


# TODO: Validate
class TMDBImporter(TMDBExternalWebsites, BaseImporter):
    # TODO: Validate
    @abstractmethod
    def download_new_watch_providers_file(self, title: Title) -> None: ...

    # TODO: Validate
    @abstractmethod
    def sync_title_watch_providers(self, title_key: str) -> None: ...

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.get_media_info(url)
        existing_title = self._preload_title(
            title=media_info.title_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_title:
            existing_title = self._upsert_title(self.source, media_info.title_key)

        return self._import_results(existing_title, media_info)


# TODO: Validate
class TMDBSeries(TMDBImporter):
    """Reads a TMDB series into records of TMDB's own."""

    # TODO: Validate
    @override
    def download_new_watch_providers_file(self, title: Title) -> None:
        if not self._watch_providers_due(title):
            return
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title.key)
        self.tv_series_watch_providers_file(
            tmdb_tv_title_id,
            tz_datetime.now().date(),
        ).download_if_outdated()

    # TODO: Validate
    @override
    def sync_title_watch_providers(self, title_key: str) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        self._get_or_create_latest_tv_series_watch_providers_file(
            tmdb_tv_title_id,
        ).download_if_outdated()
        self._process_watch_providers(
            title_key=title_key,
            files=self.incomplete_tv_series_watch_providers_files(tmdb_tv_title_id),
        )

    # TODO: Validate
    def sync_season_watch_providers(self, title_key: str, season_number: int) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        self._get_or_create_latest_tv_seasons_watch_providers_file(
            tmdb_tv_title_id=tmdb_tv_title_id,
            season_number=season_number,
        ).download_if_outdated()
        self._process_watch_providers(
            title_key,
            self.incomplete_tv_seasons_watch_providers_files(
                tmdb_tv_title_id,
                season_number,
            ),
        )

    # TODO: Validate
    @override
    def _provider_file(self, title_key: str) -> TVSeriesWatchProviders:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        return self._get_or_create_latest_tv_series_watch_providers_file(
            tmdb_tv_title_id
        )

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [season.key for season in self.chosen_seasons(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]

        wanted = set(season_keys)
        return [
            tmdb_episode_key(TMDBMediaType.tv, episode.id)
            for season in self.chosen_seasons(title_key)
            if season.key in wanted
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        groups_file = self.tv_series_episode_groups_file(tmdb_tv_title_id)
        return [
            self.get_or_create_latest_tv_series_changes_file(tmdb_tv_title_id),
            self.tv_series_details_file(tmdb_tv_title_id),
            groups_file,
            *(
                self.tv_episode_groups_details_file(option.id)
                for option in groups_file.parsed().results
            ),
            self._get_or_create_latest_tv_series_watch_providers_file(tmdb_tv_title_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        season_numbers = self.native_season_numbers(season_key, title_key)
        return [
            self.get_or_create_latest_tv_series_changes_file(tmdb_tv_title_id),
            *(
                self.tv_seasons_details_file(
                    tmdb_tv_title_id=tmdb_tv_title_id,
                    season_number=season_number,
                )
                for season_number in season_numbers
            ),
            *(
                self._get_or_create_latest_tv_seasons_watch_providers_file(
                    tmdb_tv_title_id=tmdb_tv_title_id,
                    season_number=season_number,
                )
                for season_number in season_numbers
            ),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        _, tmdb_tv_episode_id = get_media_type_and_episode_id(episode_key)
        files: list[BaseFile[Any]] = [
            self.get_or_create_latest_tv_series_changes_file(tmdb_tv_title_id),
        ]
        for season in self.chosen_seasons(title_key):
            if season.key != season_key:
                continue
            for episode in season.episodes:
                if episode.id != tmdb_tv_episode_id:
                    continue
                files.append(
                    self.tv_seasons_details_file(
                        tmdb_tv_title_id=tmdb_tv_title_id,
                        season_number=episode.season_number,
                    ),
                )
        return files

    # TODO: Validate
    def native_season_numbers(self, season_key: str, title_key: str) -> list[int]:
        group = self._chosen_episode_group(title_key)
        if group is None:
            return [self._native_season_number(season_key, title_key)]
        _, order = get_media_type_and_season_id(season_key)
        groups = group.groups
        if order >= len(groups):
            return []
        return sorted({episode.season_number for episode in groups[order].episodes})

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            series = self.tv_series_details_file(tmdb_tv_title_id).parsed()
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=series.name,
                description=series.overview,
                url=tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
                image_url=image_url(series.backdrop_path or series.poster_path),
                thumbnail_url=thumbnail_url(series.backdrop_path or series.poster_path),
                year=parse_release_year(series.first_air_date),
                media_type="Series",
                extra=title.extra if title else {},
                data_timestamp=max(data_timestamps),
                canonical_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_seasons(title, title_key, tmdb_tv_title_id, force=force)
        self._soft_delete_missing(title_key)
        self._set_title_update_frequency(title)
        return title

    # TODO: Validate
    def _set_title_update_frequency(self, title: Title) -> None:
        preload_episodes(self.session, [title])
        air_dates = [
            episode.air_date
            for season in title.active_children
            for episode in season.active_children
            if episode.air_date
        ]
        data_timestamps = self._title_files_data_timestamps(title.key)
        title.set_update_at(
            title_update_at(
                title.key,
                min(data_timestamps),
                max(air_dates) if air_dates else None,
            ),
        )

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_key: str,
        tmdb_tv_title_id: int,
        *,
        force: bool = False,
    ) -> None:
        # Whichever order the title is read in, seasons and episodes come back
        # the same shape, so nothing below asks which it was.
        for source in self.chosen_seasons(title_key):
            season = Season.get_from_memory(self.session, title, source.key)
            if self._season_is_outdated(season, title_key, force=force):
                data_timestamps = self._season_files_data_timestamps(
                    source.key, title_key
                )
                season = Season(
                    key=source.key,
                    name=source.name,
                    season_number=source.season_number,
                    sort_order=source.sort_order,
                    image_url=image_url(source.poster_path),
                    thumbnail_url=thumbnail_url(source.poster_path),
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(
                    None,
                )
            self._upsert_episodes(
                season=season,
                source=source,
                title_key=title_key,
                tmdb_tv_title_id=tmdb_tv_title_id,
                force=force,
            )
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        source: TMDBSeasonInfo,
        title_key: str,
        tmdb_tv_title_id: int,
        *,
        force: bool = False,
    ) -> None:
        season_key = source.key
        for sort_order, episode_source in enumerate(source.episodes):
            key = tmdb_episode_key(TMDBMediaType.tv, episode_source.id)
            episode = Episode.get_from_memory(self.session, season, key)
            if not self._episode_is_outdated(
                episode=episode,
                season_key=season_key,
                title_key=title_key,
                force=force,
            ):
                continue
            data_timestamps = self._episode_files_data_timestamps(
                key, season_key, title_key
            )
            still_path = episode_source.still_path or self._fallback_backdrop_path(
                tmdb_tv_title_id=tmdb_tv_title_id,
                tmdb_tv_episode_id=episode_source.id,
            )
            episode = Episode(
                key=key,
                watch_identifier=watch_identifier(self.plugin_name(), key),
                name=episode_source.name,
                description=episode_source.overview,
                url=tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
                image_url=image_url(still_path),
                thumbnail_url=thumbnail_url(still_path),
                duration=runtime_in_seconds(episode_source.runtime),
                air_date=clean_air_datetime(episode_source.air_date),
                # Episode groups still have the original episode number listed so the
                # episode number for them is based on the index.
                episode_number=(
                    sort_order + 1
                    if source.uses_episode_group
                    else episode_source.episode_number
                ),
                sort_order=sort_order,
                extra=dump_episode_extra(
                    tmdb_season_number=episode_source.season_number,
                    tmdb_episode_number=episode_source.episode_number,
                ),
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(
                None,
            )

    # TODO: Validate
    def _title_backdrop_paths(self, tmdb_tv_title_id: int) -> list[str]:
        cached: dict[int, list[str]] = self.session.info.setdefault(
            "tmdb_title_backdrop_paths",
            {},
        )
        if tmdb_tv_title_id not in cached:
            images = self.tv_series_images_file(tmdb_tv_title_id).parsed()
            cached[tmdb_tv_title_id] = [
                backdrop.file_path for backdrop in images.backdrops
            ]
        return cached[tmdb_tv_title_id]

    # TODO: Validate
    def _fallback_backdrop_path(
        self,
        tmdb_tv_title_id: int,
        tmdb_tv_episode_id: int,
    ) -> str | None:
        backdrop_paths = self._title_backdrop_paths(tmdb_tv_title_id)
        if not backdrop_paths:
            return None
        return Random(tmdb_tv_episode_id).choice(backdrop_paths)  # noqa: S311

    # TODO: Validate
    @override
    def update_title(self, title: Title, *, force: bool = False) -> None:
        # Individual files are updated based on what data has changed instead of
        # updating all of the files like most plugins.
        self._download_changes_file(title)
        self._import_all_title_changes(title)
        self._import_all_season_changes(title)
        self._preload_title(title.id, preload_episodes=True).one()
        self._upsert_title(title.source, title.key, force=force)
        self.download_new_watch_providers_file(title)
        self.sync_title_watch_providers(title.key)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        super().update_season(season)
        for season_number in self.native_season_numbers(season.key, season.title.key):
            self.sync_season_watch_providers(season.title.key, season_number)

    # TODO: Validate
    def _download_changes_file(self, title: Title) -> None:
        if title.update_at and title.update_at <= tz_datetime.now():
            _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title.key)
            self.tv_series_changes_file(
                tmdb_tv_title_id,
                tz_datetime.now().date(),
            ).download_if_outdated()

    # TODO: Validate
    def _import_all_title_changes(self, title: Title) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title.key)
        for changes_file in self.incomplete_tv_series_changes_files(tmdb_tv_title_id):
            self._import_single_title_changes(title.key, changes_file)

    # TODO: Validate
    def _import_single_title_changes(
        self,
        title_key: str,
        changes_file: TVSeriesChanges,
    ) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)

        for change in changes_file.parsed().changes:
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The details file lists the seasons, so it is read again before the
                # seasons are, otherwise a season added since the last read is named
                # by a change and found in nothing.
                self.tv_series_details_file(tmdb_tv_title_id).download_if_outdated(
                    changed_at,
                )
                # There are no episode specific files so they are grouped with the
                # seasons as they can be used to detect new episodes.
                if change.key in {"season", "episode"}:
                    season_keys: list[str]
                    # If the title uses altrernative episode ordering the only way to
                    # properly update it is to update all of the seasons.
                    title = Title.get(self.session, self.source, title_key)
                    if title and chosen_group_id(title.extra):
                        season_keys = self._season_keys_from_title_files(title_key)
                    else:
                        # Ignore the errors because these should always have a value.
                        # The type error occurs because different keys have different
                        # data structures but this is not easily added to the model
                        # because the keys are just a string.
                        season_keys = [
                            tmdb_season_key(TMDBMediaType.tv, item.value.season_id),  # type: ignore[union-attr, arg-type]
                        ]
                    for season_key in season_keys:
                        self._download_if_outdated(
                            files=self._season_files(season_key, title_key),
                            update_at=changed_at,
                        )
                        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
                        self.tv_seasons_changes_file(
                            tmdb_tv_season_id,
                            changed_at.date(),
                        ).download_if_outdated()

        changes_file.record_status = None

    # TODO: Validate
    def _import_all_season_changes(self, title: Title) -> None:
        for season_key in self._season_keys_from_title_files(title.key):
            _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
            for changes_file in self.incomplete_tv_seasons_changes_files(
                tmdb_tv_season_id,
            ):
                self._import_single_season_changes(
                    season_key=season_key,
                    title_key=title.key,
                    changes_file=changes_file,
                )

    # TODO: Validate
    def _import_single_season_changes(
        self,
        season_key: str,
        title_key: str,
        changes_file: TVSeasonsChanges,
    ) -> None:
        for change in changes_file.parsed().changes:
            if change.key != "episode":
                continue
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The season file lists the episodes and the numbering the API asks
                # for them by, so it is read again before the episode's files are
                # named, otherwise an episode added since the last read is named by
                # a change and numbered off nothing.
                self._download_if_outdated(
                    files=self._season_files(season_key, title_key),
                    update_at=changed_at,
                )
                # Ignore the errors because these should always have a value. The
                # type error occurs because different keys have different data
                # structures but this is not easily added to the model because the
                # keys are just a string.
                episode_key = tmdb_episode_key(TMDBMediaType.tv, item.value.episode_id)  # type: ignore[union-attr, arg-type]
                self._download_if_outdated(
                    files=self._episode_files(episode_key, season_key, title_key),
                    update_at=changed_at,
                )

        changes_file.record_status = None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        regex_match = re.match(self._domain_regex() + TV_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_tv_title_id = int(regex_match.group(f"{TMDBMediaType.tv}_tmdb_id"))
        self.raise_invalid_url_if_no_content(
            self.tv_series_details_file(tmdb_tv_title_id), url
        )
        return URLTitleInfo(tmdb_title_key(TMDBMediaType.tv, tmdb_tv_title_id))


# TODO: Validate
class TMDBMovie(TMDBImporter):
    """Reads a TMDB film into records of TMDB's own."""

    # TODO: Validate
    @override
    def download_new_watch_providers_file(self, title: Title) -> None:
        if not self._watch_providers_due(title):
            return
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title.key)
        self.movies_watch_providers_file(
            tmdb_movie_id,
            tz_datetime.now().date(),
        ).download_if_outdated()

    # TODO: Validate
    @override
    def sync_title_watch_providers(self, title_key: str) -> None:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        self._get_or_create_latest_movies_watch_providers_file(
            tmdb_movie_id
        ).download_if_outdated()
        self._process_watch_providers(
            title_key=title_key,
            files=self.incomplete_movies_watch_providers_files(tmdb_movie_id),
        )

    # TODO: Validate
    @override
    def _provider_file(self, title_key: str) -> MoviesWatchProviders:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return self._get_or_create_latest_movies_watch_providers_file(tmdb_movie_id)

    # TODO: Validate
    @override
    def update_title(self, title: Title, *, force: bool = False) -> None:
        super().update_title(title, force=force)
        self.download_new_watch_providers_file(title)
        self.sync_title_watch_providers(title.key)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [tmdb_season_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [tmdb_episode_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [
            self.movies_details_file(tmdb_movie_id),
            self._get_or_create_latest_movies_watch_providers_file(tmdb_movie_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [self.movies_details_file(tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [self.movies_details_file(tmdb_movie_id)]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=parsed_movie_details.title,
                description=parsed_movie_details.overview,
                url=tmdb_url(TMDBMediaType.movie, tmdb_movie_id),
                image_url=image_url(
                    parsed_movie_details.backdrop_path
                    or parsed_movie_details.poster_path,
                ),
                thumbnail_url=thumbnail_url(
                    parsed_movie_details.backdrop_path
                    or parsed_movie_details.poster_path,
                ),
                year=parse_release_year(parsed_movie_details.release_date),
                media_type="Movie",
                data_timestamp=max(data_timestamps),
                canonical_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_season(title, title_key, tmdb_movie_id, force=force)
        return title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
        tmdb_movie_id: int,
        *,
        force: bool = False,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        season_key = tmdb_season_key(TMDBMediaType.movie, tmdb_movie_id)
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title_key, force=force):
            data_timestamps = self._season_files_data_timestamps(season_key, title_key)
            season = Season(
                key=season_key,
                name=parsed_movie_details.title,
                season_number=0,
                sort_order=0,
                image_url=image_url(
                    parsed_movie_details.backdrop_path
                    or parsed_movie_details.poster_path,
                ),
                thumbnail_url=thumbnail_url(
                    parsed_movie_details.backdrop_path
                    or parsed_movie_details.poster_path,
                ),
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(
                None,
            )

        self._upsert_episode(
            season=season,
            season_key=season_key,
            title_key=title_key,
            tmdb_movie_id=tmdb_movie_id,
            force=force,
        )

        self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        season_key: str,
        title_key: str,
        tmdb_movie_id: int,
        *,
        force: bool = False,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        episode_key = tmdb_episode_key(TMDBMediaType.movie, tmdb_movie_id)
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if not self._episode_is_outdated(
            episode=episode,
            season_key=season_key,
            title_key=title_key,
            force=force,
        ):
            return
        data_timestamps = self._episode_files_data_timestamps(
            episode_key,
            season_key,
            title_key,
        )
        episode = Episode(
            key=episode_key,
            watch_identifier=watch_identifier(self.plugin_name(), episode_key),
            name=parsed_movie_details.title,
            description=parsed_movie_details.overview,
            url=tmdb_url(TMDBMediaType.movie, tmdb_movie_id),
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            duration=runtime_in_seconds(parsed_movie_details.runtime),
            air_date=clean_air_datetime(parsed_movie_details.release_date),
            episode_number=0,
            sort_order=0,
            data_timestamp=max(data_timestamps),
            season_id=season.id,
        ).upsert(season, episode)
        episode.set_update_at(
            None,
        )

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        regex_match = re.match(self._domain_regex() + MOVIE_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_movie_id = int(regex_match.group(f"{TMDBMediaType.movie}_tmdb_id"))
        self.raise_invalid_url_if_no_content(
            self.movies_details_file(tmdb_movie_id), url
        )
        return URLTitleInfo(tmdb_title_key(TMDBMediaType.movie, tmdb_movie_id))
