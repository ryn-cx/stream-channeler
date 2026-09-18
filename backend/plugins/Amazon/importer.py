# TODO: Validate
"""Writing what Prime Video says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import time, timedelta
from typing import TYPE_CHECKING, Any, override

from deforestation.detail.models import Season as ParsedSeason
from sqlalchemy import func
from sqlmodel import col, select

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from app.watch_providers.models import WatchProvider
from plugins.Amazon.shared import AmazonShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deforestation.detail.models import Episode as ParsedEpisode
    from deforestation.detail_widgets.models import Episode as WidgetEpisode

    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AmazonImporter(AmazonShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        detail_file = self.detail_file(self.link_id_from_url(url))
        self.raise_invalid_url_if_no_content(detail_file, url)
        if message := detail_file.parsed().unavailable_message:
            msg = f"{message}: {url}"
            raise InvalidURLError(msg)

        return ParsedURL(detail_file.parsed().title_key)

    # TODO: Validate
    @override  # Writes the title into every source it can be watched through.
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        if titles := self._preload_title(media_info.title_key).all():
            self.title_sources(media_info.title_key)
            return [
                result
                for title in titles
                for result in self._import_results(title, media_info)
            ]

        self._preload_and_download_files(media_info.title_key)
        results: list[URLImportResult] = []
        for source in self.title_sources(media_info.title_key):
            title = self._upsert_title(source, media_info.title_key)
            results += self._import_results(title, media_info)
        return results

    # TODO: Validate
    def _title_url(self, title_key: str) -> str:
        return self.detail_file(title_key).parsed().url

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.detail_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season and new episodes of it.
            self.detail_file(season_key),
            # Required to detect a season being taken off the title.
            self.detail_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return [self.detail_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [season.key for season in self._season_entries(title_key)]

    # TODO: Validate
    def _season_available(self, season_key: str) -> bool:
        return self.detail_file(season_key).parsed().unavailable_message is None

    # TODO: Validate
    def _season_entries(self, title_key: str) -> list[ParsedSeason]:
        parsed = self.detail_file(title_key).parsed()
        seasons = parsed.seasons or [
            ParsedSeason(
                key=parsed.link_id,
                name=parsed.title,
                season_number=parsed.season_number or 1,
                url=parsed.url,
                is_selected=True,
            ),
        ]
        season_pages = [self.detail_file(season.key) for season in seasons]
        self._preload_files(season_pages)
        self._download_if_outdated(season_pages)
        return [season for season in seasons if self._season_available(season.key)]

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        parsed = self.detail_file(title.key).parsed()
        channel_keys: list[str] = ["All Titles"]
        if parsed.purchasable:
            channel_keys.append("Purchase")
        channel_keys.extend(parsed.genres)

        for channel_key in dict.fromkeys(channel_keys):
            self.add_new_urls_to_channel(channel_key, [title.url])
        self.add_new_urls_to_channel(
            "All Titles",
            list(self.detail_file(title.key).other_title_urls_on_this_page()),
        )

    # TODO: Validate
    def title_sources(self, title_key: str) -> list[Source]:
        """Return every `Source` a title belongs to, by how it can be watched.

        A title is often offered more than one way, such as with a channel
        subscription and as a purchase, and each way is a source of its own so
        the title is found however the user can watch it. Only a title included
        with Prime belongs to Prime Video itself.
        """
        parsed = self.detail_file(title_key).parsed()
        sources = [
            self._upsert_extra_source(
                f"{channel.name} on Amazon",
                self._channel_favicon_url(channel.name),
            )
            for channel in parsed.channels
        ]
        if parsed.included_with_prime:
            sources.append(self.source)
        if parsed.purchasable:
            sources.append(
                self._upsert_extra_source(
                    "Purchase on Amazon",
                    self.favicon_url(),
                ),
            )
        # A title with no way to watch it listed still belongs somewhere.
        return sources or [self.source]

    # TODO: Validate
    def _channel_favicon_url(self, channel_name: str) -> str:
        stripped_name = func.regexp_replace(
            func.lower(col(WatchProvider.name)),
            "[^a-z0-9]",
            "",
            "g",
        )
        for name in (f"{channel_name} Amazon Channel", channel_name):
            statement = select(WatchProvider.logo_url).where(
                stripped_name == re.sub(r"[^a-z0-9]", "", name.lower()),
                col(WatchProvider.logo_url).is_not(None),
            )
            if logo_url := self.session.exec(statement).first():
                return logo_url
        return self.favicon_url()

    # TODO: Validate
    def _upsert_extra_source(self, source_key: str, favicon_url: str) -> Source:
        """Return one of the plugin's `Source`s other than its default one."""
        # Looked up against the database rather than only the session, since a
        # source other than the default is made the first time a title needs it
        # and nothing loads it back into a later session before this reads it.
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=favicon_url,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source


# TODO: Validate
class AmazonSeriesImporter(AmazonImporter):
    # TODO: Validate
    def _season_episodes(self, season_key: str) -> list[ParsedEpisode | WidgetEpisode]:
        parsed = self.detail_file(season_key).parsed()
        pages = parsed.episode_pages
        listed = [episode for episode in parsed.episodes if episode.is_available]
        if not pages:
            return list(listed)

        episodes: list[ParsedEpisode | WidgetEpisode] = []
        for index, page in enumerate(pages):
            if page.is_selected:
                episodes += listed
            else:
                episode_list = self.detail_widgets_file(season_key, index)
                episode_list.download_if_outdated()
                episodes += episode_list.episodes()
        return episodes

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.key
            for season_key in season_keys
            for episode in self._season_episodes(season_key)
        ]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        parsed = self.detail_file(title_key).parsed()
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=parsed.parent_title or parsed.title,
                description=parsed.synopsis,
                media_type="Series",
                url=parsed.url,
                image_url=parsed.image_url,
                thumbnail_url=parsed.image_url,
                year=parsed.release_year,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                min(data_timestamps) + timedelta(days=7),
            )
            title.set_genres(parsed.genres)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_entry in enumerate(self._season_entries(title.key)):
            season_key = season_entry.key
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=season_entry.url,
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(season, title.key, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self._season_episodes(season.key)):
            episode = Episode.get_from_memory(self.session, season, item.key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
                    key=item.key,
                    watch_identifier=watch_identifier(self.plugin_name(), item.key),
                    name=item.title,
                    episode_number=item.episode_number,
                    url=item.url,
                    description=item.synopsis,
                    image_url=item.image_url,
                    thumbnail_url=item.image_url,
                    duration=item.duration,
                    air_date=(
                        tz_datetime.combine(item.release_date, time.min)
                        if item.release_date
                        else None
                    ),
                    sort_order=sort_order,
                    data_timestamp=self._episode_files_data_timestamp(
                        item.key,
                        season.key,
                        title_key,
                    ),
                    season_id=season.id,
                ).upsert(season, episode)
                episode.set_update_at(None)


# TODO: Validate
class AmazonMovieImporter(AmazonImporter):
    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        # A film is the only episode of the only season of itself.
        return list(season_keys)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        parsed = self.detail_file(title_key).parsed()
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=parsed.title,
                description=parsed.synopsis,
                media_type="Movie",
                url=parsed.url,
                image_url=parsed.image_url,
                thumbnail_url=parsed.image_url,
                year=parsed.release_year,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
            )
            title.set_genres(parsed.genres)

        self._upsert_season(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, title, title.key)
        if self._season_is_outdated(season, title.key, force=force):
            season = Season(
                key=title.key,
                season_number=0,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(title.key, title.key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

        self._upsert_episode(season, title.key, force=force)
        self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if self._episode_is_outdated(
            episode,
            season.key,
            title_key,
            force=force,
        ):
            parsed = self.detail_file(title_key).parsed()
            episode = Episode(
                key=title_key,
                watch_identifier=watch_identifier(self.plugin_name(), title_key),
                name=parsed.title,
                description=parsed.synopsis,
                url=parsed.url,
                image_url=parsed.image_url,
                thumbnail_url=parsed.image_url,
                duration=parsed.duration,
                episode_number=0,
                sort_order=0,
                air_date=(
                    tz_datetime.combine(parsed.release_date, time.min)
                    if parsed.release_date
                    else None
                ),
                data_timestamp=self._episode_files_data_timestamp(
                    title_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)
