# TODO: Validate
"""Writing what Netflix says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.shared import NetflixShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.channels import ChannelKeyURL
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from meshfilm.detail_modal.models import DetailModalModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NetflixImporter(NetflixShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.title_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        title_data = self.title_file(title.key).parsed()
        channel_keys = ["All Titles", *self._title_channel_keys(title_data)]
        channel_key_urls = [
            ChannelKeyURL(channel_key, title.url) for channel_key in channel_keys
        ]
        self.add_new_urls_to_channel(channel_key_urls)
        self.add_new_urls_to_channel(self._related_channel_key_urls(title_data))

    # TODO: Validate
    def _title_channel_keys(self, title_data: DetailModalModel) -> list[str]:
        genre_tags = title_data.genre_tags.edges if title_data.genre_tags else None
        channel_keys = [
            mood_tag.display_name
            for mood_tag in title_data.mood_tags or []
            if mood_tag.display_name
        ]
        channel_keys.extend(
            edge.node.name for edge in genre_tags or [] if edge.node and edge.node.name
        )
        channel_keys.extend(
            membership.title
            for membership in title_data.title_group_memberships or []
            if membership.title
        )
        return list(dict.fromkeys(channel_keys))

    # TODO: Validate
    def _related_channel_key_urls(
        self,
        title_data: DetailModalModel,
    ) -> list[ChannelKeyURL]:
        channel_key_urls = [
            ChannelKeyURL("All Titles", self.title_url(str(similar.video_id)))
            for similar in title_data.similars or []
            if similar.video_id
        ]
        for membership in title_data.title_group_memberships or []:
            for sibling in membership.siblings or []:
                if not sibling.video_id:
                    continue
                url = self.title_url(str(sibling.video_id))
                channel_key_urls.append(ChannelKeyURL("All Titles", url))
                if membership.title:
                    channel_key_urls.append(ChannelKeyURL(membership.title, url))
        return list(dict.fromkeys(channel_key_urls))


# TODO: Validate
class NetflixSeriesImporter(NetflixImporter):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons.
        return [self.title_file(title_key), self.seasons_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            self.season_episodes_file(season_key),
            self.seasons_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_files(season_key, title_key)

    # TODO: Validate
    def _set_season_update_at(
        self,
        season: Season,
        season_video_key: str | int,
        data_timestamps: list[datetime],
    ) -> None:
        data_timestamp = min(data_timestamps)
        season.set_update_at(
            staggered_monthly_update_at(season.key, data_timestamp),
        )
        for episode in self.season_episodes_file(season_video_key).episodes():
            if episode.availability_date_messaging:
                available_at = datetime.strptime(
                    f"{episode.availability_date_messaging} {data_timestamp.year}",
                    "Available %B %d %Y",
                ).replace(tzinfo=data_timestamp.tzinfo)
                # The date listed doesn't have a specific time so check it once on the
                # date, again halway through the day and one more time at the end of the
                # day.
                season.set_update_at(available_at)
                season.set_update_at(available_at + timedelta(hours=12))
                season.set_update_at(available_at + timedelta(days=1))

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            str(season.video_id) for season in self.seasons_file(title_key).seasons()
        ]

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
            episode_keys += [
                str(episode.video_id)
                for episode in self.season_episodes_file(season_key).episodes()
            ]
        return episode_keys

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
            title_data = self.title_file(title_key).parsed()
            title = Title(
                key=title_key,
                name=title_data.title,
                description=title_data.contextual_synopsis.text,
                media_type="Series",
                year=title_data.latest_year,
                url=self.title_url(title_key),
                image_url=title_data.story_art.url,
                thumbnail_url=title_data.story_art.url,
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_data in enumerate(
            self.seasons_file(title.key).seasons(),
        ):
            season_key = str(season_data.video_id)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self._season_files_data_timestamps(
                    season_key,
                    title.key,
                )
                season = Season(
                    key=season_key,
                    name=season_data.title,
                    season_number=sort_order + 1,
                    sort_order=sort_order,
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                ).upsert(title, season)
                self._set_season_update_at(
                    season,
                    season_data.video_id,
                    data_timestamps,
                )

            self._upsert_episodes(
                season,
                title.key,
                season_data.video_id,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_video_key: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, episode_data in enumerate(
            self.season_episodes_file(season_video_key).episodes(),
        ):
            episode_key = str(episode_data.video_id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
                    key=episode_key,
                    watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                    name=episode_data.title,
                    episode_number=episode_data.number,
                    url=self.episode_url(episode_key),
                    description=episode_data.contextual_synopsis.text,
                    image_url=episode_data.artwork.url,
                    thumbnail_url=episode_data.artwork.url,
                    duration=episode_data.runtime_sec,
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
class NetflixMovieImporter(NetflixImporter):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        return [title_key]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        movie_data = self.title_file(title_key).parsed()
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            title = Title(
                key=title_key,
                name=movie_data.title,
                url=self.title_url(title_key),
                year=movie_data.latest_year,
                image_url=movie_data.story_art.url,
                thumbnail_url=movie_data.story_art.url,
                media_type="Movie",
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_season(title, movie_data, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        movie_data: DetailModalModel,
        *,
        force: bool = False,
    ) -> None:
        season_key = title.key
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title.key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(season_key, title.key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

        self._upsert_episode(season, title.key, movie_data, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        movie_data: DetailModalModel,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if self._episode_is_outdated(episode, season.key, title_key, force=force):
            episode = Episode(
                key=title_key,
                watch_identifier=watch_identifier(self.plugin_name(), title_key),
                name=movie_data.title,
                url=self.episode_url(title_key),
                image_url=movie_data.story_art.url,
                thumbnail_url=movie_data.story_art.url,
                episode_number=0,
                sort_order=0,
                data_timestamp=self._episode_files_data_timestamp(
                    title_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)
