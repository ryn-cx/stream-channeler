# TODO: Validate
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
    FileMixin,
    Schedule,
    Season,
    Series,
    Vod,
    diving_board,
)
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    PluginSearchResult,
    PluginSearchResults,
    URLImportResult,
)


class HiDive(FileMixin, register=True):
    _VERSION = "0.0.1"

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.hidive.com/series/1286`\n"
            "> `https://www.hidive.com/season/20022`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.hidive.com/video/586784`\n\n"
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        self.set_media_type_from_url(url)
        self._validate_url(url)
        show_key = self._get_show_key(url)
        show = self._import_show(show_key)
        return [URLImportResult(show=show, is_whitelist=False)]

    def _get_show_key(self, url: str) -> str:
        """Return the show key (series_id for TV, vod_id for Movie)."""
        key = self._parse_url(url)
        if self._media_type == "Movie":
            return key
        if re.match(self._tv_series_url_regex(), url):
            return key
        # season/{id} — resolve the season_id to its series_id.
        season_data = self.season_file(key).parsed()
        return str(season_data.metadata.series.series_id)

    def set_media_type_from_url(self, url: str) -> None:
        if re.match(self._movie_url_regex(), url):
            self._media_type_value = "Movie"
        elif re.match(self._tv_series_url_regex(), url) or re.match(
            self._season_url_regex(),
            url,
        ):
            self._media_type_value = "TV Show"
        else:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)

    # This does not use _media_type because that would require this to be an instance
    # method.
    @override
    def _parse_url(self, url: str) -> str:
        if match := re.match(self._tv_series_url_regex(), url):
            return match.group("series_key")
        if match := re.match(self._season_url_regex(), url):
            return match.group("season_key")
        if match := re.match(self._movie_video_url_regex(), url):
            return match.group("movie_vod_key")
        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, url: str) -> None:
        key = self._parse_url(url)
        file: Series | Season | Vod
        if self._media_type == "Movie":
            file = self.vod_file(key)
        elif re.match(self._tv_series_url_regex(), url):
            file = self.series_file(key)
        else:
            file = self.season_file(key)

        self.raise_if_invalid_file(file, url)

    def _import_show(self, key: str) -> Show:
        if show := self._preload_show(key).one_or_none():
            return show

        _cache = self._download_show_files_and_children(key)
        return self._upsert_show(self.source, show_key=key)

    def set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = show.media_type

    @override
    def update_show(self, show: Show) -> None:
        self.set_media_type_from_show(show)
        super().update_show(show)

    @override
    def update_season(self, season: SeasonModel) -> None:
        self.set_media_type_from_show(season.show)
        super().update_season(season)

    @override
    def update_episode(self, episode: Episode) -> None:
        self.set_media_type_from_show(episode.season.show)
        super().update_episode(episode)

    @override
    def update_source(self, source: Source) -> None:
        latest_schedule_file = self.get_latest_schedule_file()
        new_schedule_file = self.schedule_file(latest_schedule_file.data_timestamp)
        new_schedule_file.download_if_outdated(source.update_at)
        self._process_new_schedule_files(source)
        self._upsert_source()

    def _process_new_schedule_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()
        shows_by_name = {show.name: show for show in source.shows if show.name}

        for schedule_file in self.get_incomplete_files(
            Schedule,
            self.schedule_file,
        ):
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

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        return (
            f"{cls._tv_series_url_regex()}"
            f"|{cls._season_url_regex()}"
            f"|{cls._movie_url_regex()}"
        )

    @classmethod
    def _tv_series_url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URL: https://www.hidive.com/series/1286
        regex_string = r"\/series\/(?P<series_key>\d+)(?:\/|$)"
        return domain_regex + regex_string

    @classmethod
    def _season_url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URL: https://www.hidive.com/season/20022
        regex_string = r"\/season\/(?P<season_key>\d+)(?:\/|$)"
        return domain_regex + regex_string

    @classmethod
    def _movie_url_regex(cls) -> str:
        return cls._movie_video_url_regex()

    @classmethod
    def _movie_video_url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URL: https://www.hidive.com/video/586784
        regex_string = r"\/video\/(?P<movie_vod_key>\d+)(?:\/|$)"
        return domain_regex + regex_string

    @classmethod
    def _show_url(cls, key: str | int, media_type: str = "TV Show") -> str:
        if media_type == "Movie":
            return cls.build_url(f"video/{key}")
        return cls.build_url(f"series/{key}")

    @classmethod
    def _season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    @classmethod
    def _episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")

    def _upsert_source(self) -> Source:
        data_timestamp = self.get_latest_schedule_file().data_timestamp
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
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        if self._media_type == "Movie":
            return self._upsert_movie_show(source, show_key)
        return self._upsert_tv_show_show(source, show_key)

    def _upsert_tv_show_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        series_data = self.series_file(show_key).parsed()

        show = Show(
            key=show_key,
            name=series_data.metadata.series.title,
            url=self._show_url(show_key),
            image_url=self._series_image_url(series_data),
            media_type="TV Show",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_tv_seasons(show, show_key)
        self._set_weekly_updates_from_episodes(show)
        return show

    def _upsert_movie_show(self, source: Source, show_key: str) -> Show:
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
        ).upsert(source, existing_show)

        self._upsert_movie_seasons(show, show_key)
        self._set_weekly_updates_from_episodes(show)
        return show

    def _upsert_tv_seasons(self, show: Show, show_key: str) -> None:
        series_data = self.series_file(show_key).parsed()
        season_items = self._series_season_items(series_data)
        for sort_order, season_info in enumerate(season_items):
            season_key = str(season_info.id)
            season_data = self.season_file(season_key).parsed()
            hero = diving_board().season.extract_hero(season_data)

            if season_check := self._season_check(show, season_key, show_key):
                season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=self._season_url(season_key),
                    image_url=hero.attributes.image.attributes.source,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                ).upsert(show, season_check.record)
            else:
                season = season_check.record

            self._upsert_tv_episodes(season, show_key)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_movie_seasons(self, show: Show, show_key: str) -> None:
        for sort_order, season_key in enumerate(
            self._season_keys_from_file(show_key),
        ):
            hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())

            if season_check := self._season_check(show, season_key, show_key):
                season = SeasonModel(
                    key=season_key,
                    name=self._movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=self._show_url(show_key, "Movie"),
                    image_url=hero.attributes.image.attributes.source,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                ).upsert(show, season_check.record)
            else:
                season = season_check.record

            self._upsert_movie_episode(season, show_key)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_tv_episodes(self, season: SeasonModel, show_key: str) -> None:
        season_data = self.season_file(season.key).parsed()
        bucket = diving_board().season.extract_bucket_season(season_data)
        for sort_order, item in enumerate(bucket.attributes.items):
            episode_key = str(item.id)
            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
            )
            if not episode_check:
                continue

            vod_data = self.vod_file(episode_key).parsed()
            release_date = self._extract_release_date(vod_data)
            # HiDive puts the episode number as an E## prefix in the title.
            episode_match = re.match(r"^E(\d+)", item.title) if item.title else None
            episode_number = int(episode_match.group(1)) if episode_match else None

            Episode(
                key=episode_key,
                name=item.title,
                description=item.description,
                url=self._episode_url(episode_key),
                image_url=item.thumbnail_url,
                episode_number=episode_number,
                sort_order=sort_order,
                duration=item.duration,
                release_date=release_date,
                air_date=release_date,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert(season, episode_check.record)

        self.soft_delete_missing_episodes(season.key)

    def _upsert_movie_episode(self, season: SeasonModel, show_key: str) -> None:
        episode_key = show_key
        vod_data = self.vod_file(episode_key).parsed()
        hero = diving_board().vod.extract_hero(vod_data)

        if episode_check := self._episode_check(episode_key, season, show_key):
            release_date = self._extract_release_date(vod_data)

            Episode(
                key=episode_key,
                name=self._movie_title(hero),
                description=self._movie_description(hero),
                url=self._episode_url(episode_key),
                image_url=hero.attributes.image.attributes.source,
                episode_number=0,
                sort_order=0,
                duration=self._movie_duration(hero),
                release_date=release_date,
                air_date=release_date,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert(season, episode_check.record)

        self.soft_delete_missing_episodes(season.key)

    @staticmethod
    def _movie_title(hero: VodHeroModel) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero.attributes.actions:
            data = action.attributes.action.data
            if data.type == "VOD":
                return data.title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    @staticmethod
    def _movie_description(hero: VodHeroModel) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero.attributes.content:
            if content.attributes.text:
                return content.attributes.text
        return None

    @staticmethod
    def _movie_duration(hero: VodHeroModel) -> int | None:
        """Return the movie's runtime in seconds from the hero content."""
        for content in hero.attributes.content:
            if content.attributes.duration is not None:
                return content.attributes.duration
        return None

    _SEARCH_CARD_TYPES: ClassVar[dict[str, str]] = {
        "SERIES": "TV Show",
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
                if not (media_type := self._SEARCH_CARD_TYPES.get(type_prefix)):
                    continue
                results.append(
                    PluginSearchResult(
                        title=data.title,
                        url=self._show_url(key, media_type),
                        image_url=self._search_card_image(card),
                        media_type=media_type,
                    ),
                )
        return PluginSearchResults(has_source_selection=False, results=results)

    @staticmethod
    def _search_card_image(card: search_models.Card) -> str:
        for header in card.attributes.header:
            if header.attributes.source:
                return header.attributes.source
        msg = "Search card has no image"
        raise ValueError(msg)

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
