# TODO: Validate
"""Writing what Paramount+ says about a title into the database."""

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
from app.utils.update_at import staggered_monthly_update_at
from plugins.ParamountPlus.shared import (
    MOVIE_URL_REGEX,
    SHOW_URL_REGEX,
    ParamountPlusShared,
)
from plugins.ParamountPlus.utils import (
    build_season_key,
    movie_url,
    show_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trivial_minus.episodes.models import Datum
    from trivial_minus.movie.models import MovieModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class ParamountPlusMedia(ParamountPlusShared, BaseImporter, ABC):
    pass


# TODO: Validate
class ParamountPlusSeries(ParamountPlusMedia):
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
            self.raise_if_invalid_file(self.show_page_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _season_numbers(self, show_key: str) -> list[int]:
        return self.show_page_file(show_key).parsed().seasons

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_number: int) -> list[Datum]:
        return self.episodes_file(show_key, season_number).parsed().result.data

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        first_season = self._season_numbers(show_key)[0]
        first_episode = self._season_episodes(show_key, first_season)[0]
        return [
            TMDBLookupInfo(first_episode.series_title, TMDBMediaType.tv, None),
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect new seasons.
        return [self.show_page_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _show_key, season_number = split_season_key(season_key)
        # Required to detect new episodes.
        return [self.episodes_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_files(season_key, show_key)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
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
                episode.content_id
                for episode in self._season_episodes(show_key, season_number)
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
            first_season = self._season_numbers(show_key)[0]
            first_episode = self._season_episodes(show_key, first_season)[0]
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=first_episode.series_title,
                media_type="Series",
                url=show_url(show_key),
                image_url=first_episode.thumb.large,
                thumbnail_url=first_episode.thumb.large,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show, update_show=False)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(show.key)):
            season_key = build_season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                episodes = self._season_episodes(show.key, season_number)
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=episodes[0].season_title if episodes else None,
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
            episode_key = item.content_id
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
                name=item.title.removeprefix("EPISODE_NAME - ") if item.title else None,
                episode_number=int(item.episode_number),
                url=item.url,
                description=item.description,
                image_url=item.thumb.large,
                thumbnail_url=item.thumb.large,
                duration=item.duration_raw,
                air_date=item.airdate_iso,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class ParamountPlusMovie(ParamountPlusMedia):
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
    def _movie_data(self, show_key: str) -> MovieModel:
        return self.movie_file(show_key).parsed()

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        movie = self._movie_data(show_key)
        return [TMDBLookupInfo(movie.name, TMDBMediaType.movie, None)]

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
        movie = self._movie_data(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=movie.name,
                description=movie.description,
                media_type="Movie",
                url=movie_url(show_key),
                image_url=movie.image,
                thumbnail_url=movie.image,
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
        if not self._episode_is_outdated(
            episode,
            season.key,
            show_key,
            force=force,
        ):
            return

        movie = self._movie_data(show_key)
        data_timestamps = self.episode_data_timestamps(show_key, season.key, show_key)
        new_episode = Episode(
            key=show_key,
            watch_identifier=watch_identifier(self.plugin_name(), show_key),
            name=movie.name,
            description=movie.description,
            url=movie_url(show_key),
            image_url=movie.image,
            thumbnail_url=movie.image,
            episode_number=0,
            sort_order=0,
            air_date=movie.date_published,
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
