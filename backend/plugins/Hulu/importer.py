# TODO: Validate
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    RECOMMENDATIONS_TOPIC,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluMediaType,
)
from plugins.Hulu.shared import HuluShared
from plugins.Hulu.utils import (
    build_season_key,
    build_url,
    collection_season_key,
    collection_urls,
    episode_url,
    image_url,
    is_collection_season_key,
    season_items,
    season_numbers,
    split_collection_season_key,
    split_season_key,
    thumbnail_url,
    title_plan,
    watch_component,
    watch_components,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wholoo.movies.models import Component as MovieComponent
    from wholoo.movies.models import Item as MovieCollectionItem
    from wholoo.tv.models import Component as SeriesComponent
    from wholoo.tv.models import Item as SeriesCollectionItem

    from app.sources.models import Source
    from plugins.Hulu.files import Movie, Series
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HuluImporter(HuluShared, BaseImporter, ABC):
    # TODO: Validate
    @abstractmethod
    def _media_type_name(self) -> str: ...

    # TODO: Validate
    @abstractmethod
    @override
    def _title_files(self, title_key: str) -> Sequence[Series | Movie]: ...

    # TODO: Validate
    @abstractmethod
    def _title_components(
        self,
        title_key: str,
    ) -> Sequence[SeriesComponent | MovieComponent]: ...

    # TODO: Validate
    @abstractmethod
    def _title_record(self, source: Source, title_key: str) -> Title: ...

    # TODO: Validate
    @abstractmethod
    def _upsert_title_seasons(self, title: Title, *, force: bool = False) -> None: ...

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed_url = self.parse_url(url)
        if not (title := self._preload_title(parsed_url.title_key).one_or_none()):
            self._preload_and_download_files(parsed_url.title_key)
            title_source = self.get_title_source(parsed_url.title_key)
            title = self._upsert_title(title_source, parsed_url.title_key)
        return self._import_results(title, parsed_url)

    # TODO: Validate
    def get_title_source(self, title_key: str) -> Source:
        """Get the source for the given title key.

        Seperate sources are used for titles that require additional subscription plans.
        """
        plan = title_plan(self._title_files(title_key)[0].details())
        source_key = "Hulu"
        if plan:
            network, is_subscription = plan
            if is_subscription:
                source_key = self._channel_name(network)

        if source_key not in self._sources:
            self._sources[source_key] = self.upsert_source(source_key)

        return self._sources[source_key]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            title = self._title_record(source, title_key).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )
            title.set_genres(
                self._title_files(title_key)[0].details().entity.genre_names,
            )

        self._upsert_title_seasons(title, force=force)
        self._upsert_collection_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_collection_seasons(self, title: Title, *, force: bool = False) -> None:
        for component in watch_components(self._title_components(title.key)):
            season_key = collection_season_key(title.key, component.id)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=season_key,
                    name=component.name,
                    season_number=0,
                    sort_order=2147483647,
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_collection_episodes(season, title.key, force=force)

    # TODO: Validate
    def _upsert_collection_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(
            self._collection_items(season.key, title_key),
        ):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                hero_artwork = item.artwork.video_horizontal_hero
                hero_path = hero_artwork.path if hero_artwork else None
                episode = Episode(
                    key=episode_key,
                    watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                    name=item.name,
                    description=item.description,
                    url=episode_url(episode_key),
                    image_url=image_url(hero_path),
                    thumbnail_url=thumbnail_url(hero_path),
                    duration=item.bundle.duration if item.bundle else None,
                    air_date=item.premiere_date,
                    episode_number=sort_order + 1,
                    sort_order=sort_order,
                    data_timestamp=self._episode_files_data_timestamp(
                        episode_key,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(None)

    # TODO: Validate
    def _collection_season_keys(self, title_key: str) -> list[str]:
        return [
            collection_season_key(title_key, component.id)
            for component in watch_components(self._title_components(title_key))
        ]

    # TODO: Validate
    def _collection_items(
        self,
        season_key: str,
        title_key: str,
    ) -> list[SeriesCollectionItem | MovieCollectionItem]:
        _, component_id = split_collection_season_key(season_key)
        return list(
            watch_component(self._title_components(title_key), component_id).items,
        )

    # TODO: Validate
    def _collection_episode_keys(self, season_key: str, title_key: str) -> list[str]:
        return [str(item.id) for item in self._collection_items(season_key, title_key)]

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        details = self._title_files(title.key)[0].details()
        plan = title_plan(details)
        channel_keys = ["All Titles", self._media_type_name()]
        if plan:
            network, _ = plan
            channel_keys.append(network)
        channel_keys.extend(details.entity.genre_names)
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])
        self.add_new_urls_to_channel(
            RECOMMENDATIONS_TOPIC,
            collection_urls(self._title_components(title.key)),
        )


# TODO: Validate
class HuluSeriesImporter(HuluImporter):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return build_url(f"{HuluMediaType.SERIES}/{title_key}")

    # TODO: Validate
    @override
    def _media_type_name(self) -> str:
        return "Series"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return ParsedURL(title_key)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_key")
            episode_file = self.episode_file(episode_key)
            self.raise_invalid_url_if_no_content(episode_file, url)
            return ParsedURL(episode_file.series_key(), episode_key=episode_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[Series]:
        return [self.series_file(title_key)]

    # TODO: Validate
    @override
    def _title_components(self, title_key: str) -> Sequence[SeriesComponent]:
        return self.series_file(title_key).components()

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        if is_collection_season_key(season_key):
            return [self.series_file(title_key)]
        _, season_number = split_season_key(season_key)
        # Includes season information and the list of episodes.
        return [self.season_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_collection_season_key(season_key):
            return [self.series_file(title_key)]
        _, season_number = split_season_key(season_key)
        # Includes episode information.
        return [self.season_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            build_season_key(title_key, season_number)
            for season_number in season_numbers(self.series_file(title_key).parsed())
        ] + self._collection_season_keys(title_key)

    # TODO: Validate
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
            if is_collection_season_key(key):
                episode_keys += self._collection_episode_keys(key, title_key)
                continue
            title_key, season_number = split_season_key(key)
            episode_keys += [
                str(item.id)
                for item in season_items(
                    self.season_file(title_key, season_number).parsed(),
                )
            ]
        return episode_keys

    # TODO: Validate
    @override
    def _title_record(self, source: Source, title_key: str) -> Title:
        parsed_series = self.series_file(title_key).parsed()
        entity = parsed_series.details.entity
        return Title(
            key=title_key,
            name=parsed_series.name,
            description=entity.description,
            year=entity.premiere_date.year if entity.premiere_date else None,
            # TODO: There are mini series or documentary labels as well that could
            # be intermixed here?
            media_type=self._media_type_name(),
            url=self.title_url(title_key),
            image_url=image_url(parsed_series.artwork.program_tile.path),
            thumbnail_url=thumbnail_url(parsed_series.artwork.program_tile.path),
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        )

    # TODO: Validate
    @override
    def _upsert_title_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self.series_file(title.key).parsed()),
        ):
            season_key = build_season_key(title.key, season_number)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=season_key,
                    name=(
                        self.season_file(title.key, season_number)
                        .parsed()
                        .series_grouping_metadata.grouping_name
                    ),
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(season, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(self, season: Season, *, force: bool = False) -> None:
        title_key, season_number = split_season_key(season.key)
        items = season_items(self.season_file(title_key, season_number).parsed())
        for sort_order, item in enumerate(items):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)

            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                hero_artwork = item.artwork.video_horizontal_hero
                hero_path = hero_artwork.path if hero_artwork else None
                episode = Episode(
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
                    data_timestamp=self._episode_files_data_timestamp(
                        episode_key,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(episode.air_date)


# TODO: Validate
class HuluMovieImporter(HuluImporter):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return build_url(f"{HuluMediaType.MOVIE}/{title_key}")

    # TODO: Validate
    @override
    def _media_type_name(self) -> str:
        return "Movies"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            title_key = match.group("title_key")
        elif match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the title.key so this is
            # actually returning a title.key.
            title_key = match.group("episode_key")
        else:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.raise_invalid_url_if_no_content(self.movie_file(title_key), url)
        return ParsedURL(title_key)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[Movie]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _title_components(self, title_key: str) -> Sequence[MovieComponent]:
        return self.movie_file(title_key).components()

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key, *self._collection_season_keys(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if is_collection_season_key(season_key):
                episode_keys += self._collection_episode_keys(season_key, title_key)
            else:
                episode_keys.append(season_key)
        return episode_keys

    # TODO: Validate
    @override
    def _title_record(self, source: Source, title_key: str) -> Title:
        parsed_movie = self.movie_file(title_key).details()
        return Title(
            key=title_key,
            name=parsed_movie.entity.name,
            description=parsed_movie.entity.description,
            year=parsed_movie.entity.premiere_date.year,
            url=self.title_url(title_key),
            image_url=image_url(parsed_movie.entity.artwork.program_tile.path),
            thumbnail_url=thumbnail_url(
                parsed_movie.entity.artwork.program_tile.path,
            ),
            media_type="Movie",
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        )

    # TODO: Validate
    @override
    def _upsert_title_seasons(self, title: Title, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, title, title.key)
        if self._season_is_outdated(season, title.key, force=force):
            season = Season(
                key=title.key,
                season_number=0,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(title.key, title.key),
                title_id=title.id,
            ).upsert(title, season)
            # Movies should be updated from update_show.
            season.set_update_at(None)

        self._upsert_episode(season, force=force)

    # TODO: Validate
    def _upsert_episode(self, season: Season, *, force: bool = False) -> None:
        parsed_movie = self.movie_file(season.key).details()
        episode = Episode.get_from_memory(self.session, season, season.key)
        if self._episode_is_outdated(
            episode,
            season.key,
            season.key,
            force=force,
        ):
            episode = Episode(
                key=season.key,
                watch_identifier=watch_identifier(self.plugin_name(), season.key),
                name=parsed_movie.entity.name,
                description=parsed_movie.entity.description,
                url=episode_url(season.key),
                image_url=image_url(parsed_movie.entity.artwork.program_tile.path),
                thumbnail_url=thumbnail_url(
                    parsed_movie.entity.artwork.program_tile.path,
                ),
                duration=parsed_movie.entity.duration,
                episode_number=0,
                sort_order=0,
                data_timestamp=self._episode_files_data_timestamp(
                    season.key,
                    season.key,
                    season.key,
                ),
                season_id=season.id,
            ).upsert(season, episode)
            # Movies should be updated from update_show.
            episode.set_update_at(None)
