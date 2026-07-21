# TODO: Validate
"""HiDive plugin."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import ClassVar, override

from diving_board.search import models as search_models
from diving_board.vod import models as vod_models
from diving_board.vod.hero.models import VodHeroModel
from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season as SeasonModel
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.HiDive.files import (
    HiDiveFiles,
    Schedule,
    diving_board,
)
from plugins.HiDive.handlers import (
    HiDiveURLHandler,
    MovieURLHandler,
    SeasonURLHandler,
    SeriesURLHandler,
)
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    URLImportResult,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Add support for individual episodes of a series.
class HiDive(HiDiveFiles, URLHandlerPlugin[HiDiveURLHandler], register=True):
    """HiDive plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (SeriesURLHandler, SeasonURLHandler, MovieURLHandler)
    TMDB_PROVIDER_NAMES = ("HIDIVE",)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    @classmethod
    def _show_url(cls, key: str | int, media_type: str = "Series") -> str:
        if media_type == "Movie":
            return cls.build_url(f"video/{key}")
        return cls.build_url(f"series/{key}")

    @classmethod
    def _season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    @classmethod
    def _episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.hidive.com/series/1286`\n"
            "> `https://www.hidive.com/season/20022`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.hidive.com/video/586784`\n\n"
        )

    # Must be overridden so media type can be set
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        handler = self._get_url_handler(url)
        handler.validate_url()
        self._media_type_value = handler.media_type
        show = self._import_show(handler.show_key)
        return handler.import_results(show)

    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_schedule_file = self.schedule_file(source.data_timestamp)
        new_schedule_file.download_if_outdated(source.update_at)
        self._process_new_schedule_files(source)
        self._upsert_source()

    def _process_new_schedule_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()
        # TODO: Is there a better way to lookup shows?
        shows_by_name = {show.name: show for show in source.shows if show.name}

        for schedule_file in self.get_incomplete_files(Schedule, self.schedule_file):
            logger.info(
                "Processing schedule file: {}",
                schedule_file.database_record.key,
            )
            for page in schedule_file.parsed():
                group_list = diving_board().schedule.extract_group_list(page)
                for group in group_list.attributes.groups:
                    for card in group.attributes.cards:
                        # Layout: content[0].elements[0] is the ISO release date,
                        # elements[1] is "Show Name - Episode Title".
                        elements = card.attributes.content[0].attributes.elements
                        release_date = datetime.fromisoformat(
                            elements[0].attributes.text,  # type: ignore[arg-type]
                        ).astimezone()
                        show_name = elements[1].attributes.text.split(" - ", 1)[0]  # type: ignore[union-attr]
                        if show := shows_by_name.get(show_name):
                            show.set_update_at(release_date)
                            for season in show.seasons:
                                season.set_update_at(release_date)

            schedule_file.database_record.extra = "Completed"

    def _upsert_source(self) -> Source:
        if not (latest_schedule_file := self.get_latest_schedule_file()):
            latest_schedule_file = self.schedule_file(tz_datetime.now())
            latest_schedule_file.download_if_outdated()
        data_timestamp = latest_schedule_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=(
                "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
                "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
            ),
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if self._is_movie():
            return self._upsert_movie_show(source, show_key, force=force)
        return self._upsert_series_show(source, show_key, force=force)

    def _upsert_series_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        series_data = self.series_file(show_key).parsed()

        show = Show(
            key=show_key,
            name=series_data.metadata.series.title,
            media_type="Series",
            url=self._show_url(show_key),
            image_url=self._series_image_url(series_data),
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        )

        tmdb_show_id = self._fetch_tmdb_id(show_key, existing_show)
        show = self.tmdb.tmdb_merge_show(show, tmdb_show_id)
        show_files = self._show_files(show_key)
        show = show.upsert_and_set_update_at(source, existing_show, show_files)
        self._upsert_series_seasons(show, show_key, force=force)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_movie_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())

        show = Show(
            key=show_key,
            name=self._movie_title(hero),
            description=self._movie_description(hero),
            url=self._show_url(show_key, "Movie"),
            image_url=hero.attributes.image.attributes.source,
            media_type="Movie",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        )

        tmdb_show_id = self._fetch_tmdb_id(show_key, existing_show)
        show = self.tmdb.tmdb_merge_show(show, tmdb_show_id, "movie")
        show_files = self._show_files(show_key)
        show = show.upsert_and_set_update_at(source, existing_show, show_files)
        self._upsert_movie_seasons(show, show_key, force=force)

        return show

    def _upsert_series_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        series_data = self.series_file(show_key).parsed()
        season_items = self._series_season_items(series_data)
        for sort_order, season_info in enumerate(season_items):
            season_key = str(season_info.id)
            season_data = self.season_file(season_key).parsed()
            hero = diving_board().season.extract_hero(season_data)

            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=self._season_url(season_key),
                    image_url=hero.attributes.image.attributes.source,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self.tmdb.tmdb_merge_season(
                    season,
                    show.tmdb_id,
                    season_info.season_number,
                    "tv",
                )
                season = season.upsert_and_set_update_at(
                    show,
                    season_check.record,
                    self._season_files(season_key, show_key),
                )
            else:
                season = season_check.record

            self._upsert_series_episodes(season, show_key, force=force)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_movie_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, season_key in enumerate(
            self._season_keys_from_file(show_key),
        ):
            hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())

            if season_check := self._season_check(
                show,
                season_key,
                show_key,
                force=force,
            ):
                season = SeasonModel(
                    key=season_key,
                    name=self._movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=self._show_url(show_key, "Movie"),
                    image_url=hero.attributes.image.attributes.source,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self.tmdb.tmdb_merge_season(
                    season,
                    show.tmdb_id,
                    season.season_number,
                    "movie",
                )
                season = season.upsert_and_set_update_at(
                    show,
                    season_check.record,
                    self._season_files(season_key, show_key),
                )
            else:
                season = season_check.record

            self._upsert_movie_episode(season, show_key, force=force)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_series_episodes(
        self,
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season_data = self.season_file(season.key).parsed()
        bucket = diving_board().season.extract_bucket_season(season_data)
        for sort_order, item in enumerate(bucket.attributes.items):
            episode_key = str(item.id)
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            vod_data = self.vod_file(episode_key).parsed()
            release_date = self._extract_release_date(vod_data)
            # TODO: Double check there really is no better way to get this information.
            # HiDive puts the episode number as an E## prefix in the title.
            episode_match = re.match(r"^E(\d+)", item.title) if item.title else None
            episode_number = int(episode_match.group(1)) if episode_match else None

            episode = Episode(
                key=episode_key,
                name=item.title,
                episode_number=episode_number,
                url=self._episode_url(episode_key),
                description=item.description,
                image_url=item.thumbnail_url,
                duration=item.duration,
                sort_order=sort_order,
                release_date=release_date,
                air_date=release_date,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            episode = self.tmdb.tmdb_merge_episode(
                episode,
                season.show.tmdb_id,
                season.season_number,
                episode_number,
            )
            episode_files = self._episode_files(episode_key, season.key, show_key)
            episode.upsert_and_set_update_at(
                season,
                episode_check.record,
                episode_files,
            )

        self.soft_delete_missing_episodes(season.key)

    def _upsert_movie_episode(
        self,
        season: SeasonModel,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode_key = show_key
        vod_data = self.vod_file(episode_key).parsed()
        hero = diving_board().vod.extract_hero(vod_data)

        if episode_check := self._episode_check(
            episode_key,
            season,
            show_key,
            force=force,
        ):
            release_date = self._extract_release_date(vod_data)

            # TODO: This is ugly
            for content in hero.attributes.content:
                if content.attributes.duration is not None:
                    duration = content.attributes.duration
                    break
            else:
                duration = None

            episode = Episode(
                key=episode_key,
                name=self._movie_title(hero),
                description=self._movie_description(hero),
                url=self._episode_url(episode_key),
                image_url=hero.attributes.image.attributes.source,
                episode_number=0,
                sort_order=0,
                duration=duration,
                release_date=release_date,
                air_date=release_date,
                episode_identifier=f"{self.plugin_key()} {episode_key}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            episode = self.tmdb.tmdb_merge_episode(
                episode,
                season.show.tmdb_id,
                season.season_number,
                episode.episode_number,
                "movie",
            )
            episode_files = self._episode_files(episode_key, season.key, show_key)
            episode.upsert_and_set_update_at(
                season,
                episode_check.record,
                episode_files,
            )

        self.soft_delete_missing_episodes(season.key)

    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = show.media_type

    # Must be overridden so media type can be set
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._set_media_type_from_show(show)
        super().update_show(show, force=force)

    # Must be overridden so media type can be set
    @override
    def update_season(self, season: SeasonModel) -> None:
        self._set_media_type_from_show(season.show)
        super().update_season(season)

    # Must be overridden so media type can be set
    @override
    def update_episode(self, episode: Episode) -> None:
        self._set_media_type_from_show(episode.season.show)
        super().update_episode(episode)

    @staticmethod
    def _extract_release_date(vod_data: vod_models.VodModel) -> datetime | None:
        """Extract the release date from the "Original Premiere" tag in the VOD hero."""
        hero = diving_board().vod.extract_hero(vod_data)
        for content in hero.attributes.content:
            if not content.attributes.tags:
                continue
            for tag in content.attributes.tags:
                text = tag.attributes.text
                if text and text.startswith("Original Premiere: "):
                    date_string = text.removeprefix("Original Premiere: ")
                    return datetime.strptime(date_string, "%B %d, %Y").astimezone()
        return None

    @staticmethod
    def _movie_description(hero: VodHeroModel) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero.attributes.content:
            if content.attributes.text:
                return content.attributes.text
        return None

    CONVER_SEARCH_TYPE: ClassVar[dict[str, str]] = {
        "SERIES": "Series",
        "VOD": "Movie",
    }

    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=30)
        search_file.download_if_outdated(minimum_timestamp)

        results: list[PluginSearchResult] = []
        for element in search_file.parsed().elements:
            for card in element.attributes.cards or []:
                data = card.attributes.action.data
                type_prefix, _, key = data.id.partition("#")
                media_type = self.CONVER_SEARCH_TYPE[type_prefix]
                results.append(
                    PluginSearchResult(
                        title=data.title,
                        url=self._show_url(key, media_type),
                        image_url=self._search_card_image(card),
                        media_type=media_type,
                    ),
                )
        return PluginSearchResults(results=results)

    @staticmethod
    def _search_card_image(card: search_models.Card) -> str:
        for header in card.attributes.header:
            if header.attributes.source:
                return header.attributes.source
        msg = "Search card has no image"
        raise ValueError(msg)
