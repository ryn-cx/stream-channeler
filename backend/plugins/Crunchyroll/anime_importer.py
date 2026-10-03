# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Crunchyroll.constants import (
    EPISODE_URL_REGEX,
    SERIES_URL_REGEX,
)
from plugins.Crunchyroll.files import (
    Categories,
    Objects,
    SeasonEpisodes,
    Seasons,
    Series,
    SimilarTo,
)
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chirashi.season_episodes.models import Images as EpisodeImages
    from chirashi.seasons.models import Datum as SeasonDatum
    from chirashi.series.models import Images as SeriesImages
    from chirashi.series.models import SeriesModel

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class CrunchyrollAnimeShared(CrunchyrollShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"series/{title_key}")

    # TODO: Validate
    def similar_to_file(self, title_key: str) -> SimilarTo:
        return self._cached_file(SimilarTo, title_key)


# TODO: Validate
class CrunchyrollAnimeFiles(CrunchyrollAnimeShared, BaseUpserter, ABC):
    # TODO: Validate
    def series_file(self, title_key: str) -> Series:
        return self._cached_file(Series, title_key)

    # TODO: Validate
    def categories_file(self, title_key: str) -> Categories:
        return self._cached_file(Categories, title_key)

    # TODO: Validate
    def seasons_file(self, title_key: str) -> Seasons:
        return self._cached_file(Seasons, title_key)

    # TODO: Validate
    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._cached_file(SeasonEpisodes, season_key)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons.
            self.seasons_file(title_key),
            # Required to detect changes to the title.
            self.series_file(title_key),
            self.categories_file(title_key),
            self.similar_to_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new episodes.
            self.season_episodes_file(season_key),
            # Required to detect changes to the season.
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
        # Required to detect changes to the episode.
        return [self.season_episodes_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            season_data.id for season_data in self.seasons_file(title_key).parsed().data
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
        return [
            episode.id
            for season_key in season_keys
            for episode in self.season_episodes_file(season_key).parsed().data
        ]


# TODO: Validate
class CrunchyrollAnimeChannels(CrunchyrollAnimeFiles, ABC):
    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # This should not be possible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        categories = self.categories_file(title.key).parsed().data
        self.add_title_to_channel("All Titles", title)
        self.set_title_tag_channels(
            title,
            [category.localization.title for category in categories],
        )

    # TODO: Validate
    def _add_similar_titles_to_all_titles_channel(self, title_key: str) -> None:
        data = self.similar_to_file(title_key).parsed().data
        self.add_new_urls_to_channel(
            "All Titles",
            [self.title_url(datum.id) for datum in data],
        )

    # TODO: Validate
    @override
    def add_title_to_channels(self, title: Title) -> None:
        super().add_title_to_channels(title)
        self._add_similar_titles_to_all_titles_channel(title.key)


# TODO: Validate
class CrunchyrollAnimeUpsert(CrunchyrollAnimeChannels, ABC):
    # TODO: Validate
    @classmethod
    def episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @staticmethod
    def title_image(images: SeriesImages) -> str | None:
        """Return the widest poster a listing has, where it has one.

        The wide one first because that is the shape the artwork is shown in, the
        tall one being what is left for a listing Crunchyroll has only a portrait
        poster of.
        """
        wide = images.poster_wide
        if wide and wide[0]:
            return max(wide[0], key=lambda image: image.width).source
        tall = images.poster_tall
        if tall and tall[0]:
            return max(tall[0], key=lambda image: image.width).source
        return None

    # TODO: Validate
    @classmethod
    def title_thumbnail(cls, images: SeriesImages) -> str | None:
        wide = images.poster_wide
        if wide and wide[0]:
            return cls.nearest_thumbnail(wide[0])
        tall = images.poster_tall
        if tall and tall[0]:
            return cls.nearest_thumbnail(tall[0])
        return None

    # TODO: Validate
    @staticmethod
    def title_poster(images: SeriesImages) -> str | None:
        tall = images.poster_tall
        if tall and tall[0]:
            return max(tall[0], key=lambda image: image.width).source
        return None

    # TODO: Validate
    @classmethod
    def title_poster_thumbnail(cls, images: SeriesImages) -> str | None:
        tall = images.poster_tall
        if tall and tall[0]:
            return cls.nearest_thumbnail(tall[0])
        return None

    # TODO: Validate
    @staticmethod
    def episode_image(images: EpisodeImages) -> str | None:
        """Return the largest thumbnail an episode has, where it has one at all.

        An episode Crunchyroll has no thumbnail for has no sizes to pick from,
        and older ones have none of the field at all.
        """
        thumbnails = images.thumbnail
        if not thumbnails or not thumbnails[0]:
            return None
        return thumbnails[0][-1].source

    # TODO: Validate
    @classmethod
    def episode_thumbnail(cls, images: EpisodeImages) -> str | None:
        thumbnails = images.thumbnail
        if not thumbnails or not thumbnails[0]:
            return None
        return cls.nearest_thumbnail(thumbnails[0])

    # TODO: Validate
    @staticmethod
    def is_movie(series: SeriesModel, seasons: Sequence[SeasonDatum]) -> bool:
        return "type:movie" in series.keywords or any(
            "movie" in season.keywords for season in seasons
        )

    # TODO: Validate
    @override
    def _update_and_upsert_title(self, title: Title) -> None:
        series_file = self.series_file(title.key)
        self._download_if_outdated([series_file], title.update_at)
        if series_file.record_content is None:
            title.soft_delete()
            self.remove_title_from_plugin_channels(title)
            return
        super()._update_and_upsert_title(title)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        series_data = self.series_file(title_key).parsed()
        seasons_data = self.seasons_file(title_key).parsed().data
        upserted_title = Title(
            key=series_data.id,
            name=series_data.title,
            description=series_data.description,
            media_type=(
                MediaType.movie
                if self.is_movie(series_data, seasons_data)
                else MediaType.series
            ),
            url=self.title_url(series_data.id),
            image_url=self.title_image(series_data.images),
            thumbnail_url=self.title_thumbnail(series_data.images),
            poster_url=self.title_poster(series_data.images),
            poster_thumbnail_url=self.title_poster_thumbnail(series_data.images),
            year=series_data.series_launch_year,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(
            category.localization.title
            for category in self.categories_file(title_key).parsed().data
        )

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        seasons_file = self.seasons_file(title.key)
        for sort_order, season_data in enumerate(seasons_file.parsed().data):
            existing_season = Season.get_from_memory(
                self.session,
                title,
                season_data.id,
            )
            upserted_season = Season(
                key=season_data.id,
                name=season_data.title,
                season_number=season_data.season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_data.id,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key)
            self._set_season_update_at(upserted_season)
            for episode_data in self.season_episodes_file(season_data.id).parsed().data:
                upserted_season.set_update_at(episode_data.availability_ends)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        parsed_season_episodes = self.season_episodes_file(season.key).parsed()
        for sort_order, episode_data in enumerate(parsed_season_episodes.data):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_data.id,
            )
            Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(
                    self.plugin_name(),
                    episode_data.id,
                ),
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self.episode_url(episode_data.id),
                description=episode_data.description,
                image_url=self.episode_image(episode_data.images),
                thumbnail_url=self.episode_thumbnail(episode_data.images),
                duration=episode_data.duration_ms // 1000,
                sort_order=sort_order,
                air_date=episode_data.episode_air_date,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_data.id,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class CrunchyrollAnimeImporter(CrunchyrollAnimeUpsert):
    """Plugin for handling Crunchyroll anime and live-action series.

    Named CrunchyRollAnime because the majority of the titles it handles will be anime
    and this name makes it as clear as possible that it does not import music content.
    """

    # TODO: Validate
    def objects_file(self, episode_key: str) -> Objects:
        return self._cached_file(Objects, episode_key)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return ParsedURL(title_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_key")
            objects_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(objects_file, url)

            # Episodes for different regions have different keys. The title is always
            # imported using the original region for consistency.
            for version in objects_file.parsed().episode_metadata.versions:
                if version.original:
                    episode_key = version.guid
                    break

            original_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(original_file, url)
            return ParsedURL(
                original_file.parsed().episode_metadata.series_id,
                episode_key=episode_key,
            )

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
