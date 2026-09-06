# TODO: Validate
"""Writing what Tubi says about a title into the database."""

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
from plugins.Tubi.shared import (
    EPISODE_URL_REGEX,
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    TubiShared,
)
from plugins.Tubi.utils import (
    build_season_key,
    episode_name,
    episode_url,
    first_image,
    movie_season_key,
    movie_url,
    season_episodes,
    seasons,
    series_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugi.content.models import Child as SeasonChild
    from plugi.content.models import Child1 as EpisodeChild
    from plugi.content.models import ContentModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class TubiMedia(TubiShared, BaseImporter, ABC):
    # TODO: Validate
    def _content(self, show_key: str) -> ContentModel:
        return self.content_file(show_key).parsed()

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the show's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    def _tmdb_lookup_info(
        self,
        show_key: str,
        media_type: TMDBMediaType,
    ) -> list[TMDBLookupInfo]:
        self.content_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        content = self._content(show_key)
        return [TMDBLookupInfo(content.title, media_type, content.year)]


# TODO: Validate
class TubiSeries(TubiMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self.raise_if_invalid_file(self.content_file(show_key), url)
            return MediaInfo(show_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_key")
            self.raise_if_invalid_file(self.content_file(episode_key), url)
            series_id = self._content(episode_key).series_id
            if series_id is None:
                msg = f"Invalid {self.plugin_name()} URL: {url}"
                raise InvalidURLError(msg)
            return MediaInfo(series_id, episode_key=episode_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.tv)

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[SeasonChild]:
        return seasons(self._content(show_key))

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_id: str) -> list[EpisodeChild]:
        return season_episodes(self._content(show_key), season_id)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season.id) for season in self._seasons(show_key)
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
                episode.id for episode in self._season_episodes(show_key, season_id)
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
            content = self._content(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Series",
                url=series_url(show_key),
                image_url=first_image(content.backgrounds),
                thumbnail_url=first_image(content.backgrounds),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, season_content in enumerate(self._seasons(show.key)):
            season_key = build_season_key(show.key, season_content.id)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    name=season_content.title,
                    season_number=int(season_content.id),
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(
                season,
                show.key,
                season_content.id,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_id: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_content in enumerate(
            self._season_episodes(show_key, season_id),
        ):
            episode_key = episode_content.id
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
                name=episode_name(episode_content.title),
                description=episode_content.description,
                episode_number=int(episode_content.episode_number),
                url=episode_url(episode_key),
                image_url=first_image(episode_content.thumbnails),
                thumbnail_url=first_image(episode_content.thumbnails),
                duration=episode_content.duration,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class TubiMovie(TubiMedia):
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
            self.raise_if_invalid_file(self.content_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(show_key, TMDBMediaType.movie)

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [movie_season_key(show_key)]

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
        content = self._content(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=content.title,
                description=content.description,
                media_type="Movie",
                url=movie_url(show_key),
                image_url=first_image(content.backgrounds),
                thumbnail_url=first_image(content.backgrounds),
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
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(self, show: Show, *, force: bool = False) -> None:
        season_key = movie_season_key(show.key)
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

        content = self._content(show_key)
        data_timestamps = self.episode_data_timestamps(show_key, season.key, show_key)
        new_episode = Episode(
            key=show_key,
            watch_identifier=watch_identifier(self.plugin_name(), show_key),
            name=content.title,
            description=content.description,
            episode_number=0,
            url=movie_url(show_key),
            image_url=first_image(content.backgrounds),
            thumbnail_url=first_image(content.backgrounds),
            duration=content.duration,
            sort_order=0,
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
