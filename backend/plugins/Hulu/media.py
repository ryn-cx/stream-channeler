from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from sqlmodel import col, select

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.Hulu.shared import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluShared,
)
from plugins.Hulu.utils import (
    HuluMediaType,
    episode_url,
    image_url,
    build_season_key,
    season_items,
    season_numbers,
    show_url,
    split_season_key,
    thumbnail_url,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HuluMedia(HuluShared, BaseImporter, ABC):
    # TODO: Validate
    @abstractmethod
    def _add_show_to_media_type_channel(self, url: str) -> None: ...

    # TODO: Validate
    def add_show_to_plugin_channels(self, show: Show) -> None:
        if not show.url: # Should be impossible.
            msg = "Show.url is not set."
            raise AttributeError(msg)

        self._add_show_to_all_titles_channel(show.url)
        self._add_show_to_media_type_channel(show.url)

    # TODO: Validate
    def _add_show_to_all_titles_channel(self, url: str) -> None:
        self.add_urls_to_plugin_channel(
            "Hulu - All Titles",
            "All Titles on Hulu.",
            [url],
        )


class HuluSeries(HuluMedia):
    # TODO: Validate
    @override
    def _add_show_to_media_type_channel(self, url: str) -> None:
        self.add_urls_to_plugin_channel(
            "Hulu - TV Series",
            "All TV Series on Hulu.",
            [url],
        )

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self.raise_if_invalid_file(self.series_file(show_key), url)
            return MediaInfo(show_key)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_key")
            episode_hub = self.episode_file(episode_key)
            # raise_if_invalid_file is not needed because the URL was already checked by
            # the redirect follower.
            return MediaInfo(
                str(episode_hub.parsed().details.vod_items.focus.entity.series_id),
                episode_key=episode_key,
            )

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    # TODO: Validate
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        parsed_series = self.series_file(show_key).parsed()
        return [
            TMDBLookupInfo(
                parsed_series.name,
                TMDBMediaType.tv,
                parsed_series.details.entity.premiere_date.year,
            ),
        ]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Includes show information and the list of seasons.
        return [self.series_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, season_number = split_season_key(season_key)
        # Includes season information and the list of episodes.
        return [self.season_file(show_key, season_number)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, season_number = split_season_key(season_key)
        # Includes episode information.
        return [self.season_file(show_key, season_number)]

    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season_number)
            for season_number in season_numbers(self.series_file(show_key).parsed())
        ]

    @override
    # TODO: Validate
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for key in season_keys:
            show_key, season_number = split_season_key(key)
            episode_keys += [
                str(item.id)
                for item in season_items(
                    self.season_file(show_key, season_number).parsed(),
                )
            ]
        return episode_keys

    @override
    # TODO: Validate
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(existing_show, force=force):
            parsed_series = self.series_file(show_key).parsed()
            entity = parsed_series.details.entity
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=show_key,
                name=parsed_series.name,
                description=entity.description,
                # TODO: There are mini series or documentary labels as well that could
                # be intermixed here?
                media_type="Series",
                url=show_url(show_key, HuluMediaType.SERIES),
                image_url=image_url(parsed_series.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(parsed_series.artwork.program_tile.path),
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            existing_show = new_show.upsert(source, existing_show)
            existing_show.set_update_at(None, data_timestamps)

        self._upsert_seasons(existing_show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(existing_show)
        self.add_show_to_plugin_channels(existing_show)

        return existing_show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self.series_file(show.key).parsed()),
        ):
            season_key = build_season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=(
                        self.season_file(show.key, season_number)
                        .parsed()
                        .series_grouping_metadata.grouping_name
                    ),
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._set_season_update_at(season, show.key, season_number)
            self._upsert_episodes(season, force=force)

    # TODO: Validate
    def _set_season_update_at(
        self,
        season: Season,
        show_key: str,
        season_number: int,
    ) -> None:
        start_dates = [
            item.bundle.availability.start_date
            for item in season_items(self.season_file(show_key, season_number).parsed())
        ]
        if not start_dates:
            return

        now = tz_datetime.now()
        for start_date in start_dates:
            if start_date > now:
                season.set_update_at(start_date)

        season.set_update_at(max(start_dates) + timedelta(days=7))

    # TODO: Validate
    def _upsert_episodes(self, season: Season, *, force: bool = False) -> None:
        show_key, season_number = split_season_key(season.key)
        items = season_items(self.season_file(show_key, season_number).parsed())
        for sort_order, item in enumerate(items):
            # Don't import media that cannot actually be watched because that would just
            # be annoying for the users.
            if item.bundle.availability.start_date > tz_datetime.now():
                continue

            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)

            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            hero_artwork = item.artwork.video_horizontal_hero
            hero_path = hero_artwork.path if hero_artwork else None
            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.name,
                episode_number=int(item.number),
                url=episode_url(episode_key),
                description=item.description,
                image_url=image_url(hero_path),
                thumbnail_url=thumbnail_url(hero_path),
                duration=item.duration,
                air_date=item.premiere_date,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


class HuluMovie(HuluMedia):
    # TODO: Validate
    @override
    def _add_show_to_media_type_channel(self, url: str) -> None:
        self.add_urls_to_plugin_channel(
            "Hulu - Movies",
            "All Movies on Hulu.",
            [url],
        )

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            show_key = match.group("movie_key")
        elif match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the show.key so this is
            # actually returning a show.key.
            show_key = match.group("episode_key")
        else:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.raise_if_invalid_file(self.movie_file(show_key), url)
        return MediaInfo(show_key)

    @override
    # TODO: Validate
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        parsed_movie = self.movie_file(show_key).parsed()
        return [
            TMDBLookupInfo(
                parsed_movie.name,
                TMDBMediaType.movie,
                parsed_movie.details.entity.premiere_date.year,
            ),
        ]

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    # TODO: Validate
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [show_key]

    @override
    # TODO: Validate
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return list(season_keys)

    @override
    # TODO: Validate
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        parsed_movie = self.movie_file(show_key).parsed()
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=show_key,
                name=parsed_movie.name,
                description=parsed_movie.details.entity.description,
                url=show_url(show_key, HuluMediaType.MOVIE),
                image_url=image_url(parsed_movie.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(parsed_movie.artwork.program_tile.path),
                media_type="Movie",
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_season(show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)
        self.add_show_to_plugin_channels(show)

        return show

    def _upsert_season(self, show: Show, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, show, show.key)
        if self._season_is_outdated(season, show.key, force=force):
            data_timestamps = self.season_data_timestamps(show.key, show.key)
            new_season = Season(
                key=show.key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, force=force)

    def _upsert_episode(self, season: Season, *, force: bool = False) -> None:
        parsed_movie = self.movie_file(season.key).parsed()
        episode = Episode.get_from_memory(self.session, season, season.key)
        if self._episode_is_outdated(
            episode,
            season.key,
            season.key,
            force=force,
        ):
            data_timestamps = self.episode_data_timestamps(
                season.key,
                season.key,
                season.key,
            )
            new_episode = Episode(
                key=season.key,
                watch_identifier=watch_identifier(self.plugin_name(), season.key),
                name=parsed_movie.name,
                description=parsed_movie.details.entity.description,
                url=episode_url(season.key),
                image_url=image_url(parsed_movie.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(parsed_movie.artwork.program_tile.path),
                duration=parsed_movie.details.entity.duration,
                episode_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
