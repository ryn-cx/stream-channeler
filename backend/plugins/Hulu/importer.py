from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, override

from sqlmodel import col, select

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.titles.models import Title
from plugins.Hulu.shared import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluShared,
)
from plugins.Hulu.utils import (
    HuluMediaType,
    build_season_key,
    episode_url,
    genre_names,
    image_url,
    plan_channel_description,
    plan_channel_name,
    season_items,
    season_numbers,
    split_season_key,
    thumbnail_url,
    title_plan,
    title_url,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.Hulu.files import Movie, Series
    from plugins.Hulu.utils import HuluPlan
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


class HuluImporter(HuluShared, BaseImporter, ABC):
    @abstractmethod
    def _media_type_name(self) -> str: ...

    @abstractmethod
    @override
    def _title_files(self, title_key: str) -> Sequence[Series | Movie]: ...

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        if title := self._preload_title(media_info.title_key).one_or_none():
            return self._import_results(title, media_info)

        title_source = self.get_title_source(media_info.title_key)
        title = self.upsert_title(title_source, media_info.title_key)
        return self._import_results(title, media_info)

    def get_title_source(self, title_key: str) -> Source:
        plan = title_plan(self._title_files(title_key)[0].parsed())
        source_key = "Hulu"
        if plan and plan.is_subscription:
            source_key += f" ({plan.network})"

        if source_key not in self._sources:
            self._sources[source_key] = self.upsert_source(source_key)

        return self._sources[source_key]

    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        page = self._title_files(title.key)[0].parsed()
        plan = title_plan(page)
        self._add_title_to_all_titles_channel(title.url)
        self._add_title_to_plan_channel(title.url, self._media_type_name(), plan)
        if plan:
            self._add_title_to_plan_channel(title.url, plan.network, plan)
        for genre in genre_names(page):
            self._add_title_to_plan_channel(title.url, genre, plan)
        if not (plan and plan.is_subscription):
            self._add_title_to_included_titles_channel(title.url)

    def _add_title_to_all_titles_channel(self, url: str) -> None:
        channel_name = "Hulu - All Titles"
        channel_description = "All Titles on Hulu."
        channel = self.get_or_create_channel(channel_name, channel_description)
        self.add_new_urls_to_channel(channel, [url])

    def _add_title_to_plan_channel(
        self,
        url: str,
        subject: str,
        plan: HuluPlan | None,
    ) -> None:
        channel_name = plan_channel_name(subject, plan)
        channel_description = plan_channel_description(subject, plan)
        channel = self.get_or_create_channel(channel_name, channel_description)
        self.add_new_urls_to_channel(channel, [url])

    def _add_title_to_included_titles_channel(self, url: str) -> None:
        channel_name = "Hulu - Included Titles"
        channel_description = "All Titles included with a Hulu subscription."
        channel = self.get_or_create_channel(channel_name, channel_description)
        self.add_new_urls_to_channel(channel, [url])


class HuluSeriesImporter(HuluImporter):
    @override
    def _media_type_name(self) -> str:
        return "Series"

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def extract_media_info(self, url: str) -> URLTitleInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("series_key")
            self.raise_if_invalid_file(self.series_file(title_key), url)
            return URLTitleInfo(title_key)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_key")
            episode_file = self.episode_file(episode_key)
            self.raise_if_invalid_file(episode_file, url)
            return URLTitleInfo(
                str(episode_file.parsed().details.vod_items.focus.entity.series_id),
                episode_key=episode_key,
            )

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def tmdb_lookup_info(
        self,
        title_key: str,
    ) -> list[TMDBLookupInfo]:
        parsed_series = self.series_file(title_key).parsed()
        year = None
        if premiere_date := parsed_series.details.entity.premiere_date:
            year = premiere_date.year
        return [TMDBLookupInfo(parsed_series.name, TMDBMediaType.tv, year)]

    @override
    def _title_files(self, title_key: str) -> Sequence[Series]:
        return [self.series_file(title_key)]

    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, season_number = split_season_key(season_key)
        # Includes season information and the list of episodes.
        return [self.season_file(title_key, season_number)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, season_number = split_season_key(season_key)
        # Includes episode information.
        return [self.season_file(title_key, season_number)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            build_season_key(title_key, season_number)
            for season_number in season_numbers(self.series_file(title_key).parsed())
        ]

    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for key in season_keys:
            title_key, season_number = split_season_key(key)
            episode_keys += [
                str(item.id)
                for item in season_items(
                    self.season_file(title_key, season_number).parsed(),
                )
            ]
        return episode_keys

    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(existing_title, force=force):
            parsed_series = self.series_file(title_key).parsed()
            entity = parsed_series.details.entity
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=parsed_series.name,
                description=entity.description,
                # TODO: There are mini series or documentary labels as well that could
                # be intermixed here?
                media_type=self._media_type_name(),
                url=title_url(title_key, HuluMediaType.SERIES),
                image_url=image_url(parsed_series.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(parsed_series.artwork.program_tile.path),
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            existing_title = new_title.upsert(source, existing_title)
            existing_title.set_update_at(None, data_timestamps)

        self._upsert_seasons(existing_title, force=force)
        self._soft_delete_missing(title_key)
        self.link_title_to_tmdb(existing_title)
        self.add_title_to_plugin_channels(existing_title)

        return existing_title

    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self.series_file(title.key).parsed()),
        ):
            season_key = build_season_key(title.key, season_number)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = Season(
                    key=season_key,
                    name=(
                        self.season_file(title.key, season_number)
                        .parsed()
                        .series_grouping_metadata.grouping_name
                    ),
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    def _upsert_episodes(self, season: Season, *, force: bool = False) -> None:
        title_key, season_number = split_season_key(season.key)
        items = season_items(self.season_file(title_key, season_number).parsed())
        for sort_order, item in enumerate(items):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)

            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            hero_artwork = item.artwork.video_horizontal_hero
            hero_path = hero_artwork.path if hero_artwork else None
            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                title_key,
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
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(episode.air_date, data_timestamps)


class HuluMovieImporter(HuluImporter):
    @override
    def _media_type_name(self) -> str:
        return "Movies"

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def extract_media_info(self, url: str) -> URLTitleInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            title_key = match.group("movie_key")
        elif match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the title.key so this is
            # actually returning a title.key.
            title_key = match.group("episode_key")
        else:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.raise_if_invalid_file(self.movie_file(title_key), url)
        return URLTitleInfo(title_key)

    @override
    def tmdb_lookup_info(
        self,
        title_key: str,
    ) -> list[TMDBLookupInfo]:
        parsed_movie = self.movie_file(title_key).parsed()
        year = parsed_movie.details.entity.premiere_date.year
        return [TMDBLookupInfo(parsed_movie.name, TMDBMediaType.movie, year)]

    @override
    def _title_files(self, title_key: str) -> Sequence[Movie]:
        return [self.movie_file(title_key)]

    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key]

    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return list(season_keys)

    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        parsed_movie = self.movie_file(title_key).parsed()
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=parsed_movie.name,
                description=parsed_movie.details.entity.description,
                url=title_url(title_key, HuluMediaType.MOVIE),
                image_url=image_url(parsed_movie.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(parsed_movie.artwork.program_tile.path),
                media_type="Movie",
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamps)

        self._upsert_season(title, force=force)
        self._soft_delete_missing(title_key)
        self.link_title_to_tmdb(title)
        self.add_title_to_plugin_channels(title)

        return title

    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, title, title.key)
        if self._season_is_outdated(season, title.key, force=force):
            data_timestamps = self.season_data_timestamps(title.key, title.key)
            new_season = Season(
                key=title.key,
                season_number=0,
                sort_order=0,
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            )
            season = new_season.upsert(title, season)
            # Movies should be updated from update_show.
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
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            # Movies should be updated from update_show.
            episode.set_update_at(None, data_timestamps)
