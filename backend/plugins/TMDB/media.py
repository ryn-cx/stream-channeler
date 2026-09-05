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
    tmdb_show_key,
)
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.TMDB.external_websites import TMDBExternalWebsites
from plugins.TMDB.files import (
    MoviesWatchProviders,
    TVSeasonsChanges,
    TVSeriesChanges,
    TVSeriesWatchProviders,
)
from plugins.TMDB.shared import (
    MOVIE_URL_REGEX,
    TV_URL_REGEX,
)
from plugins.TMDB.utils import (
    SeasonInfo,
    image_url,
    parse_release_year,
    thumbnail_url,
    tiel_url,
)
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v3.files import (
    COMPLETED_STATUS,
    BaseFile,
)
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo


def clean_air_datetime(air_date: str | date) -> datetime | None:
    """Return a datetime for the air date and replaces empty strings with None.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if isinstance(air_date, str):
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


def runtime_in_seconds(runtime: int | None) -> int | None:
    # If the runtime is not known the API returns None. In all other cases it returns
    # the runtime in minutes.
    return runtime * 60 if runtime else None


# TODO: Validate
class TMDBMedia(TMDBExternalWebsites, BaseImporter):
    # TODO: Validate
    @abstractmethod
    def download_new_watch_providers_file(self, show: Show) -> None: ...

    # TODO: Validate
    @abstractmethod
    def sync_show_watch_providers(self, show_key: str) -> None: ...

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        existing_show = self._preload_show(
            show=media_info.show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            existing_show = self.upsert_show(self.source, media_info.show_key)
            self._import_title_from_external_websites(
                media_info.show_key,
                existing_show,
            )

        return self._import_results(existing_show, media_info)


# TODO: Validate
class TMDBSeries(TMDBMedia):
    """Reads a TMDB series into records of TMDB's own."""

    # TODO: Validate
    @override
    def download_new_watch_providers_file(self, show: Show) -> None:
        if not self._watch_providers_due(show):
            return
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show.key)
        self.tv_series_watch_providers_file(
            tmdb_tv_show_id=tmdb_tv_show_id,
            downloaded_at=tz_datetime.now().date(),
        ).download_if_outdated()

    # TODO: Validate
    @override
    def sync_show_watch_providers(self, show_key: str) -> None:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        self.latest_tv_series_watch_providers_file(
            tmdb_tv_show_id,
        ).download_if_outdated()
        self._process_watch_providers(
            show_key=show_key,
            files=self.incomplete_tv_series_watch_providers_files(tmdb_tv_show_id),
        )

    # TODO: Validate
    def sync_season_watch_providers(self, show_key: str, season_number: int) -> None:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        self.latest_tv_seasons_watch_providers_file(
            tmdb_tv_show_id=tmdb_tv_show_id,
            season_number=season_number,
        ).download_if_outdated()
        self._process_watch_providers(
            show_key,
            self.incomplete_tv_seasons_watch_providers_files(
                tmdb_tv_show_id,
                season_number,
            ),
        )

    # TODO: Validate
    @override
    def _provider_file(self, show_key: str) -> TVSeriesWatchProviders:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        return self.latest_tv_series_watch_providers_file(tmdb_tv_show_id)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [season.key for season in self.chosen_seasons(show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]

        wanted = set(season_keys)
        return [
            tmdb_episode_key(TMDBMediaType.tv, episode.id)
            for season in self.chosen_seasons(show_key)
            if season.key in wanted
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        groups_file = self.tv_series_episode_groups_file(tmdb_tv_show_id)
        return [
            self.latest_tv_series_changes_file(tmdb_tv_show_id),
            self.tv_series_details_file(tmdb_tv_show_id),
            groups_file,
            *(
                self.tv_episode_groups_details_file(option.id)
                for option in groups_file.parsed().results
            ),
            self.latest_tv_series_watch_providers_file(tmdb_tv_show_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        season_numbers = self.native_season_numbers(season_key, show_key)
        return [
            self.latest_tv_series_changes_file(tmdb_tv_show_id),
            *(
                self.tv_seasons_details_file(
                    tmdb_tv_show_id=tmdb_tv_show_id,
                    season_number=season_number,
                )
                for season_number in season_numbers
            ),
            *(
                self.latest_tv_seasons_watch_providers_file(
                    tmdb_tv_show_id=tmdb_tv_show_id,
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
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        _, tmdb_tv_episode_id = get_media_type_and_episode_id(episode_key)
        files: list[BaseFile[Any]] = [
            self.latest_tv_series_changes_file(tmdb_tv_show_id),
        ]
        for season in self.chosen_seasons(show_key):
            if season.key != season_key:
                continue
            for episode in season.episodes:
                if episode.id != tmdb_tv_episode_id:
                    continue
                files.extend(
                    (
                        # Contains all of the episode information except for
                        # translations.
                        self.tv_seasons_details_file(
                            tmdb_tv_show_id=tmdb_tv_show_id,
                            season_number=episode.season_number,
                        ),
                        self.tv_episodes_translations_file(
                            tmdb_tv_show_id=tmdb_tv_show_id,
                            season_number=episode.season_number,
                            episode_number=episode.episode_number,
                        ),
                    ),
                )
        return files

    # TODO: Validate
    def native_season_numbers(self, season_key: str, show_key: str) -> list[int]:
        group = self._chosen_episode_group(show_key)
        if group is None:
            return [self._native_season_number(season_key, show_key)]
        _, order = get_media_type_and_season_id(season_key)
        groups = group.groups
        if order >= len(groups):
            return []
        return sorted({episode.season_number for episode in groups[order].episodes})

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series = self.tv_series_details_file(tmdb_tv_show_id).parsed()
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=series.name,
                description=series.overview,
                url=tiel_url(TMDBMediaType.tv, tmdb_tv_show_id),
                image_url=image_url(series.backdrop_path or series.poster_path),
                thumbnail_url=thumbnail_url(series.backdrop_path or series.poster_path),
                year=parse_release_year(series.first_air_date),
                media_type="Series",
                extra=show.extra if show else {},
                data_timestamp=data_timestamp,
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons(show, show_key, tmdb_tv_show_id, force=force)
        self._soft_delete_missing(show_key)
        self._set_dynamic_update_at(show)
        return show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        tmdb_tv_show_id: int,
        *,
        force: bool = False,
    ) -> None:
        # Whichever order the title is read in, seasons and episodes come back
        # the same shape, so nothing below asks which it was.
        for source in self.chosen_seasons(show_key):
            season = Season.get_from_memory(self.session, show, source.key)
            if self._season_is_outdated(season, show_key, force=force):
                data_timestamps = self.season_data_timestamps(source.key, show_key)
                data_timestamp = data_timestamps[0]
                new_season = Season(
                    key=source.key,
                    name=source.name,
                    season_number=source.season_number,
                    sort_order=source.sort_order,
                    image_url=image_url(source.poster_path),
                    thumbnail_url=thumbnail_url(source.poster_path),
                    data_timestamp=data_timestamp,
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(
                    None,
                    data_timestamps,
                )
            self._upsert_episodes(
                season=season,
                source=source,
                show_key=show_key,
                tmdb_tv_show_id=tmdb_tv_show_id,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        source: SeasonInfo,
        show_key: str,
        tmdb_tv_show_id: int,
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
                show_key=show_key,
                force=force,
            ):
                continue
            data_timestamps = self.episode_data_timestamps(key, season_key, show_key)
            data_timestamp = data_timestamps[0]
            still_path = episode_source.still_path or self._fallback_backdrop_path(
                tmdb_tv_show_id=tmdb_tv_show_id,
                tmdb_tv_episode_id=episode_source.id,
            )
            new_episode = Episode(
                key=key,
                watch_identifier=watch_identifier(self.plugin_name(), key),
                name=episode_source.name,
                description=episode_source.overview,
                url=tiel_url(TMDBMediaType.tv, tmdb_tv_show_id),
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
                data_timestamp=data_timestamp,
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(
                None,
                data_timestamps,
            )

    # TODO: Validate
    def _show_backdrop_paths(self, tmdb_tv_show_id: int) -> list[str]:
        cached: dict[int, list[str]] = self.session.info.setdefault(
            "tmdb_show_backdrop_paths",
            {},
        )
        if tmdb_tv_show_id not in cached:
            images = self.tv_series_images_file(tmdb_tv_show_id).parsed()
            cached[tmdb_tv_show_id] = [
                backdrop.file_path for backdrop in images.backdrops
            ]
        return cached[tmdb_tv_show_id]

    # TODO: Validate
    def _fallback_backdrop_path(
        self,
        tmdb_tv_show_id: int,
        tmdb_tv_episode_id: int,
    ) -> str | None:
        backdrop_paths = self._show_backdrop_paths(tmdb_tv_show_id)
        if not backdrop_paths:
            return None
        return Random(tmdb_tv_episode_id).choice(backdrop_paths)  # noqa: S311

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        # Individual files are updated based on what data has changed instead of
        # updating all of the files like most plugins.
        self._download_changes_file(show)
        self._import_all_show_changes(show)
        self._import_all_season_changes(show)
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, force=force)
        self.download_new_watch_providers_file(show)
        self.sync_show_watch_providers(show.key)
        self._import_title_from_external_websites(show.key, show)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        super().update_season(season)
        for season_number in self.native_season_numbers(season.key, season.show.key):
            self.sync_season_watch_providers(season.show.key, season_number)

    # TODO: Validate
    def _download_changes_file(self, show: Show) -> None:
        if show.update_at and show.update_at <= tz_datetime.now():
            _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show.key)
            self.tv_series_changes_file(
                tmdb_tv_show_id=tmdb_tv_show_id,
                downloaded_to=tz_datetime.now().date(),
            ).download_if_outdated()

    # TODO: Validate
    def _import_all_show_changes(self, show: Show) -> None:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show.key)
        for changes_file in self.incomplete_tv_series_changes_files(tmdb_tv_show_id):
            self._import_single_show_changes(show.key, changes_file)

    # TODO: Validate
    def _import_single_show_changes(
        self,
        show_key: str,
        changes_file: TVSeriesChanges,
    ) -> None:
        _, tmdb_tv_show_id = get_media_type_and_tmdb_id(show_key)

        for change in changes_file.parsed().changes:
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The details file lists the seasons, so it is read again before the
                # seasons are, otherwise a season added since the last read is named
                # by a change and found in nothing.
                self.tv_series_details_file(tmdb_tv_show_id).download_if_outdated(
                    changed_at,
                )
                # There are no episode specific files so they are grouped with the
                # seasons as they can be used to detect new episodes.
                if change.key in {"season", "episode"}:
                    season_keys: list[str]
                    # If the show uses altrernative episode ordering the only way to
                    # properly update it is to update all of the seasons.
                    show = Show.get(self.session, self.source, show_key)
                    if show and chosen_group_id(show.extra):
                        season_keys = self._season_keys_from_show_files(show_key)
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
                            files=self._season_files(season_key, show_key),
                            update_at=changed_at,
                        )
                        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
                        self.tv_seasons_changes_file(
                            tmdb_tv_season_id=tmdb_tv_season_id,
                            changed_on=changed_at.date(),
                        ).download_if_outdated()

        changes_file.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def _import_all_season_changes(self, show: Show) -> None:
        for season_key in self._season_keys_from_show_files(show.key):
            _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
            for changes_file in self.incomplete_tv_seasons_changes_files(
                tmdb_tv_season_id,
            ):
                self._import_single_season_changes(
                    season_key=season_key,
                    show_key=show.key,
                    changes_file=changes_file,
                )

    # TODO: Validate
    def _import_single_season_changes(
        self,
        season_key: str,
        show_key: str,
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
                    files=self._season_files(season_key, show_key),
                    update_at=changed_at,
                )
                # Ignore the errors because these should always have a value. The
                # type error occurs because different keys have different data
                # structures but this is not easily added to the model because the
                # keys are just a string.
                episode_key = tmdb_episode_key(TMDBMediaType.tv, item.value.episode_id)  # type: ignore[union-attr, arg-type]
                self._download_if_outdated(
                    files=self._episode_files(episode_key, season_key, show_key),
                    update_at=changed_at,
                )

        changes_file.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        regex_match = re.match(self._domain_regex() + TV_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_tv_show_id = int(regex_match.group(f"{TMDBMediaType.tv}_tmdb_id"))
        self.raise_if_invalid_file(self.tv_series_details_file(tmdb_tv_show_id), url)
        return MediaInfo(tmdb_show_key(TMDBMediaType.tv, tmdb_tv_show_id))


# TODO: Validate
class TMDBMovie(TMDBMedia):
    """Reads a TMDB film into records of TMDB's own."""

    # TODO: Validate
    @override
    def download_new_watch_providers_file(self, show: Show) -> None:
        if not self._watch_providers_due(show):
            return
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show.key)
        self.movies_watch_providers_file(
            tmdb_movie_id=tmdb_movie_id,
            downloaded_at=tz_datetime.now().date(),
        ).download_if_outdated()

    # TODO: Validate
    @override
    def sync_show_watch_providers(self, show_key: str) -> None:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        self.latest_movies_watch_providers_file(tmdb_movie_id).download_if_outdated()
        self._process_watch_providers(
            show_key=show_key,
            files=self.incomplete_movies_watch_providers_files(tmdb_movie_id),
        )

    # TODO: Validate
    @override
    def _provider_file(self, show_key: str) -> MoviesWatchProviders:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return self.latest_movies_watch_providers_file(tmdb_movie_id)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        super().update_show(show, force=force)
        self.download_new_watch_providers_file(show)
        self.sync_show_watch_providers(show.key)
        self._import_title_from_external_websites(show.key, show)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_season_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_episode_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return [
            self.movies_details_file(tmdb_movie_id),
            self.latest_movies_watch_providers_file(tmdb_movie_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_movie_id)]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(show_key)
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=parsed_movie_details.title,
                description=parsed_movie_details.overview,
                url=tiel_url(TMDBMediaType.movie, tmdb_movie_id),
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
                data_timestamp=data_timestamp,
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_season(show, show_key, tmdb_movie_id, force=force)
        self._set_dynamic_update_at(show)
        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        tmdb_movie_id: int,
        *,
        force: bool = False,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        season_key = tmdb_season_key(TMDBMediaType.movie, tmdb_movie_id)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show_key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, show_key)
            data_timestamp = data_timestamps[0]
            new_season = Season(
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
                data_timestamp=data_timestamp,
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(
                None, data_timestamps,
            )

        self._upsert_episode(
            season=season,
            season_key=season_key,
            show_key=show_key,
            tmdb_movie_id=tmdb_movie_id,
            force=force,
        )

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        season_key: str,
        show_key: str,
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
            show_key=show_key,
            force=force,
        ):
            return
        data_timestamps = self.episode_data_timestamps(
            episode_key,
            season_key,
            show_key,
        )
        data_timestamp = data_timestamps[0]
        new_episode = Episode(
            key=episode_key,
            watch_identifier=watch_identifier(self.plugin_name(), episode_key),
            name=parsed_movie_details.title,
            description=parsed_movie_details.overview,
            url=tiel_url(TMDBMediaType.movie, tmdb_movie_id),
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
            data_timestamp=data_timestamp,
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(
            None,
            data_timestamps,
        )

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        regex_match = re.match(self._domain_regex() + MOVIE_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_movie_id = int(regex_match.group(f"{TMDBMediaType.movie}_tmdb_id"))
        self.raise_if_invalid_file(self.movies_details_file(tmdb_movie_id), url)
        return MediaInfo(tmdb_show_key(TMDBMediaType.movie, tmdb_movie_id))
