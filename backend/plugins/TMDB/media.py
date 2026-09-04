# TODO: Validate
"""Reading a TMDB title as the half of the catalogue it belongs to."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from random import Random
from typing import Any, override

from app.canonical_media.keys import (
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_show_key,
    watch_identifier,
)
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import dump_episode_extra, show_chosen_group_id
from plugins.TMDB.files import (
    TVSeasonsChanges,
    TVSeriesChanges,
)
from plugins.TMDB.keys import (
    get_media_type_and_tmdb_id,
    parse_episode_key,
    parse_season_key,
)
from plugins.TMDB.external_websites import TMDBExternalWebsites
from plugins.TMDB.shared import (
    MOVIE_URL_REGEX,
    TV_URL_REGEX,
)
from plugins.TMDB.urls import media_url
from plugins.TMDB.utils import (
    SeasonSource,
    air_datetime,
    backdrop_image_url,
    backdrop_thumbnail_url,
    duration_seconds,
    poster_image_url,
    poster_original_url,
    release_year,
    still_image_url,
    still_thumbnail_url,
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


# TODO: Validate
class TMDBMedia(TMDBExternalWebsites, BaseImporter):
    # TODO: Validate
    def _import_title_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        # TMDB should always be canonical so if it is imported with a caonical_show
        # something has gone wrong.
        if canonical_show is not None:
            msg = "canonical_show should be None when importing TMDB URLs."
            raise InvalidURLError(msg)

        show_key = self._url_to_show_key(url)
        existing_show = self._preload_show(
            show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            existing_show = self.upsert_show(self.source, show_key)
            self._import_title_from_external_websites(show_key, existing_show)

        return self._import_results(existing_show)


# TODO: Validate
class TMDBSeries(TMDBMedia):
    """Reads a TMDB series into records of TMDB's own."""

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [season.key for season in self.series_seasons(show_key)]

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
            for season in self.series_seasons(show_key)
            if season.key in wanted
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        groups_file = self.tv_series_episode_groups_file(tmdb_id)
        groups = groups_file.parsed_or_none()
        options = groups.results if groups else []
        return [
            self.latest_tv_series_changes_file(show_key),
            self.tv_series_details_file(tmdb_id),
            groups_file,
            *(self.tv_episode_groups_details_file(option.id) for option in options),
            self.latest_tv_series_watch_providers_file(tmdb_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        show = Show.get(self.session, self.source, show_key)
        season = Season.get(self.session, show, season_key) if show else None
        due = self._watch_providers_due(season)
        return [
            *self._season_detail_files(season_key, show_key),
            *(
                self.tv_seasons_watch_providers_file(
                    tmdb_id,
                    season_number,
                    tz_datetime.now().date(),
                )
                if due
                else self.latest_tv_seasons_watch_providers_file(
                    tmdb_id,
                    season_number,
                )
                for season_number in self.native_season_numbers(season_key, show_key)
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
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        _, episode_tmdb_id = parse_episode_key(episode_key)
        files: list[BaseFile[Any]] = [
            # Contains all of the episode information except for translations.
            *self._season_detail_files(season_key, show_key),
        ]
        for season in self.series_seasons(show_key):
            if season.key != season_key:
                continue
            for episode in season.episodes:
                if episode.id != episode_tmdb_id:
                    continue
                files.append(
                    self.tv_episodes_translations_file(
                        tmdb_id,
                        episode.native_season_number,
                        episode.native_episode_number,
                    ),
                )
        return files

    # TODO: Validate
    def _season_detail_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        changes_file = self.latest_tv_series_changes_file(show_key)
        group_id = show_chosen_group_id(self.session, self.source, show_key)
        if group_id is not None:
            return [changes_file, self.tv_episode_groups_details_file(group_id)]
        return [
            changes_file,
            self.tv_seasons_details_file(
                tmdb_id,
                self._native_season_number(season_key, show_key),
            ),
        ]

    # TODO: Validate
    def native_season_numbers(self, season_key: str, show_key: str) -> list[int]:
        group_id = show_chosen_group_id(self.session, self.source, show_key)
        if group_id is None:
            return [self._native_season_number(season_key, show_key)]
        _, order = parse_season_key(season_key)
        groups = self.tv_episode_groups_details_file(group_id).parsed().groups
        if order >= len(groups):
            return []
        return sorted({episode.season_number for episode in groups[order].episodes})

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> Show:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        show = self._stored_title(source, show_key)
        if self._show_is_outdated(show, update_at, force=force):
            series = self.tv_series_details_file(tmdb_id).parsed(update_at)
            data_timestamp = self.show_data_timestamp(show_key, update_at)
            new_show = Show(
                key=show_key,
                name=series.name,
                description=series.overview,
                url=media_url(TMDBMediaType.tv, tmdb_id),
                image_url=backdrop_image_url(series.backdrop_path)
                or poster_original_url(series.poster_path),
                thumbnail_url=backdrop_thumbnail_url(series.backdrop_path)
                or poster_image_url(series.poster_path),
                year=release_year(series.first_air_date),
                media_type="TV Show",
                extra=show.extra,
                data_timestamp=data_timestamp,
                update_at=data_timestamp + timedelta(days=7),
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_seasons(show, show_key, tmdb_id, update_at, force=force)
        self._soft_delete_missing(show_key)
        return show

    # TODO: Validate
    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        tmdb_id: int,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        # Whichever order the title is read in, seasons and episodes come back
        # the same shape, so nothing below asks which it was.
        for source in self.series_seasons(show_key, update_at):
            season = self._stored_season(show, source.key)
            if self._season_is_outdated(season, show_key, update_at, force=force):
                data_timestamp = self.season_data_timestamp(
                    source.key,
                    show_key,
                    update_at,
                )
                new_season = Season(
                    key=source.key,
                    name=source.name,
                    season_number=source.season_number,
                    sort_order=source.season_number,
                    image_url=poster_original_url(source.poster_path),
                    thumbnail_url=poster_image_url(source.poster_path),
                    data_timestamp=data_timestamp,
                    update_at=None,
                    show_id=show.id,
                )
                season = self._upsert_season_object(
                    new_season,
                    show,
                    season,
                    show_key,
                )
            self._upsert_episodes(
                season,
                source,
                show_key,
                tmdb_id,
                update_at,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(  # noqa: PLR0913
        self,
        season: Season,
        source: SeasonSource,
        show_key: str,
        tmdb_id: int,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        season_key = source.key
        for sort_order, episode_source in enumerate(source.episodes):
            key = tmdb_episode_key(TMDBMediaType.tv, episode_source.id)
            episode = self._stored_episode(season, key)
            if not self._episode_is_outdated(
                episode,
                season_key,
                show_key,
                update_at,
                force=force,
            ):
                continue
            data_timestamp = self.episode_data_timestamp(
                key,
                season_key,
                show_key,
                update_at,
            )
            still_path = episode_source.still_path or self._fallback_backdrop_path(
                tmdb_id,
                episode_source.id,
            )
            new_episode = Episode(
                key=key,
                watch_identifier=watch_identifier(self.plugin_name(), key),
                name=episode_source.name,
                description=episode_source.overview,
                url=media_url(TMDBMediaType.tv, tmdb_id),
                image_url=still_image_url(still_path),
                thumbnail_url=still_thumbnail_url(still_path),
                duration=duration_seconds(episode_source.runtime),
                air_date=air_datetime(episode_source.air_date),
                episode_number=episode_source.number,
                sort_order=sort_order,
                extra=dump_episode_extra(
                    episode_source.native_season_number,
                    episode_source.native_episode_number,
                ),
                data_timestamp=data_timestamp,
                update_at=None,
                season_id=season.id,
            )
            self._upsert_episode_object(new_episode, season, episode, show_key)

    # TODO: Validate
    def _show_backdrop_paths(self, tmdb_id: int) -> list[str]:
        cached: dict[int, list[str]] = self.session.info.setdefault(
            "tmdb_show_backdrop_paths",
            {},
        )
        if tmdb_id not in cached:
            images = self.tv_series_images_file(tmdb_id).parsed_or_none()
            cached[tmdb_id] = (
                [backdrop.file_path for backdrop in images.backdrops] if images else []
            )
        return cached[tmdb_id]

    # TODO: Validate
    def _fallback_backdrop_path(
        self,
        tmdb_id: int,
        episode_tmdb_id: int,
    ) -> str | None:
        backdrop_paths = self._show_backdrop_paths(tmdb_id)
        if not backdrop_paths:
            return None
        return Random(episode_tmdb_id).choice(backdrop_paths)  # noqa: S311

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
        self.download_due_watch_providers_file(show)
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
            self.tv_series_changes_file(
                show.key, tz_datetime.now().date(),
            ).download_if_outdated()

    # TODO: Validate
    def _import_all_show_changes(self, show: Show) -> None:
        for changes_file in self.incomplete_tv_series_changes_files(show.key):
            self._import_single_show_changes(show.key, changes_file)

    # TODO: Validate
    def _import_single_show_changes(
        self,
        show_key: str,
        changes_file: TVSeriesChanges,
    ) -> None:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)

        for change in changes_file.parsed().changes:
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The details file lists the seasons, so it is read again before the
                # seasons are, otherwise a season added since the last read is named
                # by a change and found in nothing.
                self.tv_series_details_file(tmdb_id).download_if_outdated(changed_at)
                # There are no episode specific files so they are grouped with the
                # seasons as they can be used to detect new episodes.
                if change.key in {"season", "episode"}:
                    season_keys: list[str]
                    # If the show uses altrernative episode ordering the only way to
                    # properly update it is to update all of the seasons.
                    if show_chosen_group_id(self.session, self.source, show_key):
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
                            self._season_files(season_key, show_key),
                            changed_at,
                        )
                        self.tv_seasons_changes_file(
                            season_key,
                            changed_at.date(),
                        ).download_if_outdated()

        changes_file.database_record.status = COMPLETED_STATUS

    def _import_all_season_changes(self, show: Show) -> None:
        for season_key in self._season_keys_from_show_files(show.key):
            for changes_file in self.incomplete_tv_seasons_changes_files(season_key):
                self._import_single_season_changes(
                    season_key,
                    show.key,
                    changes_file,
                )

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
                    self._season_files(season_key, show_key),
                    changed_at,
                )
                # Ignore the errors because these should always have a value. The
                # type error occurs because different keys have different data
                # structures but this is not easily added to the model because the
                # keys are just a string.
                episode_key = tmdb_episode_key(TMDBMediaType.tv, item.value.episode_id)  # type: ignore[union-attr, arg-type]
                self._download_if_outdated(
                    self._episode_files(episode_key, season_key, show_key),
                    changed_at,
                )

        changes_file.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        match = re.match(self._domain_regex() + TV_URL_REGEX, url)
        if match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_id = int(match.group(f"{TMDBMediaType.tv}_tmdb_id"))
        self.raise_if_invalid_file(self.tv_series_details_file(tmdb_id), url)
        return tmdb_show_key(TMDBMediaType.tv, tmdb_id)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        return self._import_title_url(url, canonical_show)


# TODO: Validate
class TMDBMovie(TMDBMedia):
    """Reads a TMDB film into records of TMDB's own."""

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        super().update_show(show, force=force)
        self.download_due_watch_providers_file(show)
        self.sync_show_watch_providers(show.key)
        self._import_title_from_external_websites(show.key, show)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_season_key(media_type, tmdb_id)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_episode_key(media_type, tmdb_id)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [
            self.movies_details_file(tmdb_id),
            self.latest_movies_watch_providers_file(tmdb_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_id)]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> Show:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        movie = self.movies_details_file(tmdb_id).parsed(update_at)
        show = self._stored_title(source, show_key)
        if self._show_is_outdated(show, update_at, force=force):
            data_timestamp = self.show_data_timestamp(show_key, update_at)
            new_show = Show(
                key=show_key,
                name=movie.title,
                description=movie.overview,
                url=media_url(TMDBMediaType.movie, tmdb_id),
                image_url=backdrop_image_url(movie.backdrop_path)
                or poster_original_url(movie.poster_path),
                thumbnail_url=backdrop_thumbnail_url(movie.backdrop_path)
                or poster_image_url(movie.poster_path),
                year=release_year(movie.release_date),
                media_type="Movie",
                extra=show.extra,
                data_timestamp=data_timestamp,
                update_at=data_timestamp + timedelta(days=7),
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = self._upsert_show_object(new_show, source, show, show_key)

        self._upsert_season(show, show_key, tmdb_id, update_at, force=force)
        return show

    # TODO: Validate
    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        tmdb_id: int,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        movie = self.movies_details_file(tmdb_id).parsed(update_at)
        key = tmdb_season_key(TMDBMediaType.movie, tmdb_id)
        season = self._stored_season(show, key)
        if self._season_is_outdated(season, show_key, update_at, force=force):
            data_timestamp = self.season_data_timestamp(key, show_key, update_at)
            new_season = Season(
                key=key,
                name=movie.title,
                season_number=0,
                sort_order=0,
                image_url=poster_original_url(movie.poster_path),
                thumbnail_url=poster_image_url(movie.poster_path),
                data_timestamp=data_timestamp,
                update_at=None,
                show_id=show.id,
            )
            season = self._upsert_season_object(new_season, show, season, show_key)

        self._upsert_episode(
            season,
            key,
            show_key,
            tmdb_id,
            update_at,
            force=force,
        )

    # TODO: Validate
    def _upsert_episode(  # noqa: PLR0913
        self,
        season: Season,
        season_key: str,
        show_key: str,
        tmdb_id: int,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        movie = self.movies_details_file(tmdb_id).parsed(update_at)
        key = tmdb_episode_key(TMDBMediaType.movie, tmdb_id)
        episode = self._stored_episode(season, key)
        if not self._episode_is_outdated(
            episode,
            season_key,
            show_key,
            update_at,
            force=force,
        ):
            return
        data_timestamp = self.episode_data_timestamp(
            key,
            season_key,
            show_key,
            update_at,
        )
        new_episode = Episode(
            key=key,
            watch_identifier=watch_identifier(self.plugin_name(), key),
            name=movie.title,
            description=movie.overview,
            url=media_url(TMDBMediaType.movie, tmdb_id),
            image_url=backdrop_image_url(movie.backdrop_path),
            thumbnail_url=backdrop_thumbnail_url(movie.backdrop_path),
            duration=duration_seconds(movie.runtime),
            air_date=air_datetime(movie.release_date),
            episode_number=0,
            sort_order=0,
            data_timestamp=data_timestamp,
            update_at=None,
            season_id=season.id,
        )
        self._upsert_episode_object(new_episode, season, episode, show_key)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        match = re.match(self._domain_regex() + MOVIE_URL_REGEX, url)
        if match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_id = int(match.group(f"{TMDBMediaType.movie}_tmdb_id"))
        self.raise_if_invalid_file(self.movies_details_file(tmdb_id), url)
        return tmdb_show_key(TMDBMediaType.movie, tmdb_id)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        return self._import_title_url(url, canonical_show)
