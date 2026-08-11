# TODO: Validate
from __future__ import annotations

import re
from typing import override

from diving_board.series import models as series_models
from diving_board.vod.hero.models import VodHeroModel

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.HiDive.files import HiDiveFiles, diving_board


# TODO: Validate
class HelperMixin(HiDiveFiles, register=False):
    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = show.media_type

    # TODO: Validate
    @staticmethod
    def _series_image_url(series_data: series_models.SeriesModel) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.image:
                return element.attributes.image.attributes.source
        msg = "No image element found in series file."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def _movie_title(hero: VodHeroModel) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero.attributes.actions:
            data = action.attributes.action.data
            if data.type == "VOD":
                return data.title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    # TODO: Validate
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        media_type: MediaType
        if self._is_movie():
            self.vod_file(show_key).download_if_outdated()
            hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())
            name = self._movie_title(hero)
            media_type = MediaType.movie
        else:
            self.series_file(show_key).download_if_outdated()
            name = self.series_file(show_key).parsed().metadata.series.title
            media_type = MediaType.tv
        return self._tmdb_search_media(name, media_type)

    # TODO: Validate
    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        if self._is_movie():
            return None
        for season_info in self._series_season_items(
            self.series_file(show_key).parsed(),
        ):
            if str(season_info.id) == season_key:
                return season_info.season_number
        return None

    # TODO: Validate
    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        if self._is_movie():
            return None
        bucket = diving_board().season.extract_bucket_season(
            self.season_file(season_key).parsed(),
        )
        for item in bucket.attributes.items:
            if str(item.id) == episode_key:
                match = re.match(r"^E(\d+)", item.title) if item.title else None
                return int(match.group(1)) if match else None
        return None

    # TODO: Validate
    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie() else MediaType.tv

    # TODO: Validate
    @classmethod
    def _show_url(cls, key: str | int, media_type: str = "Series") -> str:
        if media_type == "Movie":
            return cls.build_url(f"video/{key}")
        return cls.build_url(f"series/{key}")

    # TODO: Validate
    @classmethod
    def _season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")
