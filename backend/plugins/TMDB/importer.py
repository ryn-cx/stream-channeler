# TODO: Validate
"""Reading a TMDB title as the half of the catalogue it belongs to."""

from __future__ import annotations

import re
from abc import ABC
from collections.abc import Sequence
from datetime import date, datetime
from random import Random
from typing import Any, override

from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.watch_providers import record_watch_providers
from app.tmdb_media.keys import (
    watch_identifier,
)
from app.tmdb_media.tmdb import (
    dump_episode_extra,
    get_media_type_and_episode_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import (
    TMDBSeasonInfo,
    image_url,
    parse_release_year,
    thumbnail_url,
    tmdb_url,
    watch_provider_names,
    watch_provider_offerings,
)
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.files import (
    BaseFile,
)
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL


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
class TMDBImporter(TMDBShared, BaseImporter, ABC):
    # TODO: Validate
    def _record_unmatched_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        """Write down the services carrying `title` that nothing here carries.

        Read on every import rather than once, since which services carry a
        title is the half of this that changes, and the file it is read from is
        downloaded with the rest of the title's either way.
        """
        from app.titles.service.unmatched import (  # noqa: PLC0415
            record_unmatched_providers,
        )

        record_unmatched_providers(
            self.session,
            title,
            watch_provider_names(watch_providers),
        )

    # TODO: Validate
    def _record_watch_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        record_watch_providers(
            self.session,
            title,
            watch_provider_offerings(watch_providers),
        )

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        existing_title = self._preload_title(
            title=media_info.title_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_title:
            self._preload_and_download_files(media_info.title_key)
            existing_title = self._upsert_title(self.source, media_info.title_key)

        return self._import_results(existing_title, media_info)


# TODO: Validate
class TMDBSeries(TMDBImporter):
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
        groups_file.download_if_outdated()
        return [
            self.tv_series_details_file(tmdb_tv_title_id),
            groups_file,
            *(
                self.tv_episode_groups_details_file(option.id)
                for option in groups_file.parsed().results
            ),
            self.tv_series_watch_providers_file(tmdb_tv_title_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        season_numbers = self.native_season_numbers(season_key, title_key)
        return [
            *(
                self.tv_seasons_details_file(
                    tmdb_tv_title_id=tmdb_tv_title_id,
                    season_number=season_number,
                )
                for season_number in season_numbers
            ),
            *(
                self.tv_seasons_watch_providers_file(
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
        files: list[BaseFile[Any]] = []
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
    ) -> Title:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        series = self.tv_series_details_file(tmdb_tv_title_id).parsed()
        upserted_title = Title(
            key=title_key,
            name=series.name,
            description=series.overview,
            url=tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
            image_url=image_url(series.backdrop_path or series.poster_path),
            thumbnail_url=thumbnail_url(series.backdrop_path or series.poster_path),
            poster_url=image_url(series.poster_path),
            poster_thumbnail_url=thumbnail_url(series.poster_path),
            year=parse_release_year(series.first_air_date),
            score=series.vote_average,
            popularity=series.popularity,
            original_language=series.original_language,
            media_type=MediaType.series,
            extra=existing_title.extra if existing_title else {},
            data_timestamp=self._title_files_data_timestamp(title_key),
            tmdb_title_validated_at=tz_datetime.now(),
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(genre.name for genre in series.genres)
        upserted_title.set_spoken_languages(
            {
                language.iso_639_1: language.english_name
                for language in series.spoken_languages
            },
        )

        self._upsert_seasons(upserted_title, title_key, tmdb_tv_title_id)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self._set_title_update_at(upserted_title)
        series_watch_providers = self.tv_series_watch_providers_file(
            tmdb_tv_title_id,
        ).parsed()
        self._record_unmatched_providers(upserted_title, series_watch_providers)
        self._record_watch_providers(upserted_title, series_watch_providers)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_key: str,
        tmdb_tv_title_id: int,
    ) -> None:
        for source in self.chosen_seasons(title_key):
            existing_season = Season.get_from_memory(self.session, title, source.key)
            upserted_season = Season(
                key=source.key,
                name=source.name,
                season_number=source.season_number,
                sort_order=source.sort_order,
                image_url=image_url(source.poster_path),
                thumbnail_url=thumbnail_url(source.poster_path),
                data_timestamp=self._season_files_data_timestamp(
                    source.key,
                    title_key,
                ),
                title_id=title.id,
                update_at=None,
            ).upsert(title, existing_season)
            self._upsert_episodes(
                season=upserted_season,
                source=source,
                title_key=title_key,
                tmdb_tv_title_id=tmdb_tv_title_id,
            )
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        source: TMDBSeasonInfo,
        title_key: str,
        tmdb_tv_title_id: int,
    ) -> None:
        season_key = source.key
        for sort_order, episode_source in enumerate(source.episodes):
            key = tmdb_episode_key(TMDBMediaType.tv, episode_source.id)
            existing_episode = Episode.get_from_memory(self.session, season, key)
            still_path = episode_source.still_path or self._fallback_backdrop_path(
                tmdb_tv_title_id=tmdb_tv_title_id,
                tmdb_tv_episode_id=episode_source.id,
            )
            Episode(
                key=key,
                watch_identifier=watch_identifier(self.plugin_name(), key),
                name=episode_source.name,
                description=episode_source.overview,
                url=tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
                image_url=image_url(still_path),
                thumbnail_url=thumbnail_url(still_path),
                duration=runtime_in_seconds(episode_source.runtime),
                air_date=clean_air_datetime(episode_source.air_date),
                # Episode groups still have the original episode number listed so
                # the episode number for them is based on the index.
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
                data_timestamp=self._episode_files_data_timestamp(
                    key,
                    season_key,
                    title_key,
                ),
                season_id=season.id,
                update_at=None,
            ).upsert(season, existing_episode)

    # TODO: Validate
    def _title_backdrop_paths(self, tmdb_tv_title_id: int) -> list[str]:
        cached: dict[int, list[str]] = self.session.info.setdefault(
            "tmdb_title_backdrop_paths",
            {},
        )
        if tmdb_tv_title_id not in cached:
            images_file = self.tv_series_images_file(tmdb_tv_title_id)
            images_file.download_if_outdated()
            images = images_file.parsed()
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
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        regex_match = re.match(self._domains_regex() + TV_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_tv_title_id = int(regex_match.group("title_key"))
        self.raise_invalid_url_if_no_content(
            self.tv_series_details_file(tmdb_tv_title_id),
            url,
        )
        return ParsedURL(tmdb_title_key(TMDBMediaType.tv, tmdb_tv_title_id))


# TODO: Validate
class TMDBMovie(TMDBImporter):
    """Reads a TMDB film into records of TMDB's own."""

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
            self.movies_watch_providers_file(tmdb_movie_id),
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
    ) -> Title:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        existing_title = Title.get_from_memory(self.session, source, title_key)
        upserted_title = Title(
            key=title_key,
            name=parsed_movie_details.title,
            description=parsed_movie_details.overview,
            url=tmdb_url(TMDBMediaType.movie, tmdb_movie_id),
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            poster_url=image_url(parsed_movie_details.poster_path),
            poster_thumbnail_url=thumbnail_url(parsed_movie_details.poster_path),
            year=parse_release_year(parsed_movie_details.release_date),
            score=parsed_movie_details.vote_average,
            popularity=parsed_movie_details.popularity,
            original_language=parsed_movie_details.original_language,
            media_type=MediaType.movie,
            data_timestamp=self._title_files_data_timestamp(title_key),
            tmdb_title_validated_at=tz_datetime.now(),
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(
            genre.name for genre in parsed_movie_details.genres
        )
        upserted_title.set_spoken_languages(
            {
                language.iso_639_1: language.english_name
                for language in parsed_movie_details.spoken_languages
            },
        )

        self._upsert_season(upserted_title, title_key, tmdb_movie_id)
        movie_watch_providers = self.movies_watch_providers_file(tmdb_movie_id).parsed()
        self._record_unmatched_providers(upserted_title, movie_watch_providers)
        self._record_watch_providers(upserted_title, movie_watch_providers)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
        tmdb_movie_id: int,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        season_key = tmdb_season_key(TMDBMediaType.movie, tmdb_movie_id)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            name=parsed_movie_details.title,
            season_number=0,
            sort_order=0,
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            data_timestamp=self._season_files_data_timestamp(season_key, title_key),
            title_id=title.id,
            update_at=None,
        ).upsert(title, existing_season)

        self._upsert_episode(
            season=upserted_season,
            season_key=season_key,
            title_key=title_key,
            tmdb_movie_id=tmdb_movie_id,
        )

        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        season_key: str,
        title_key: str,
        tmdb_movie_id: int,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        episode_key = tmdb_episode_key(TMDBMediaType.movie, tmdb_movie_id)
        existing_episode = Episode.get_from_memory(self.session, season, episode_key)
        Episode(
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
            data_timestamp=self._episode_files_data_timestamp(
                episode_key,
                season_key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        regex_match = re.match(self._domains_regex() + MOVIE_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_movie_id = int(regex_match.group("title_key"))
        self.raise_invalid_url_if_no_content(
            self.movies_details_file(tmdb_movie_id),
            url,
        )
        return ParsedURL(tmdb_title_key(TMDBMediaType.movie, tmdb_movie_id))
