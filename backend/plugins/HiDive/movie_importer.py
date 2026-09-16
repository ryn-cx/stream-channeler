# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season as SeasonModel
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, MOVIE_URL_REGEX
from plugins.HiDive.shared import HiDiveShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from diving_board.vod import models as vod_models

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HiDiveMovieFiles(HiDiveShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(episode_key)]

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
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return list(season_keys)


# TODO: Validate
class HiDiveMovieChannels(HiDiveMovieFiles, ABC):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"video/{title_key}")

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        elements = self.vod_file(title.key).parsed().elements
        self.add_new_urls_to_channel(
            "All Titles",
            [title.url, *self.related_title_urls(elements)],
        )


# TODO: Validate
class HiDiveMovieUpsert(HiDiveMovieChannels, ABC):
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
            hero = self.vod_hero(self.vod_file(title_key).parsed())
            premiere = self.release_date(hero)
            title = Title(
                key=title_key,
                name=self.movie_title(hero),
                description=self.movie_description(hero),
                year=premiere.year if premiere else None,
                url=self.title_url(title_key),
                image_url=self.hero_image_url(hero),
                thumbnail_url=self.hero_image_url(hero),
                media_type=MOVIE_MEDIA_TYPE,
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
        for sort_order, season_key in enumerate(
            self._season_keys_from_title_files(title.key),
        ):
            hero = self.vod_hero(self.vod_file(title.key).parsed())

            season = SeasonModel.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                season = SeasonModel(
                    key=season_key,
                    name=self.movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=self.title_url(title.key),
                    image_url=self.hero_image_url(hero),
                    thumbnail_url=self.hero_image_url(hero),
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episode(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: SeasonModel,
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
            hero = self.vod_hero(self.vod_file(title_key).parsed())
            episode = Episode(
                key=title_key,
                watch_identifier=watch_identifier(self.plugin_name(), title_key),
                name=self.movie_title(hero),
                description=self.movie_description(hero),
                url=self.episode_url(title_key),
                image_url=self.hero_image_url(hero),
                thumbnail_url=self.hero_image_url(hero),
                episode_number=0,
                sort_order=0,
                duration=self.movie_duration(hero),
                air_date=self.release_date(hero),
                data_timestamp=self._episode_files_data_timestamp(
                    title_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)

    # TODO: Validate
    @classmethod
    def movie_title(cls, hero: vod_models.Element) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero.attributes.actions or []:
            data = action.attributes.action.data
            if data.type == "VOD":
                return data.title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    # TODO: Validate
    @classmethod
    def movie_description(cls, hero: vod_models.Element) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero.attributes.content or []:
            if content.attributes.text:
                return content.attributes.text
        return None

    # TODO: Validate
    @classmethod
    def movie_duration(cls, hero: vod_models.Element) -> int | None:
        """Return how long the movie runs for, in seconds."""
        for content in hero.attributes.content or []:
            if content.attributes.duration is not None:
                return content.attributes.duration
        return None


# TODO: Validate
class HiDiveMovieImporter(HiDiveMovieUpsert):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.vod_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
