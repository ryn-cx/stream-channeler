# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override

from notaplanet import NotAPlanet
from notaplanet.exceptions import ItemNotFoundError, SeriesNotFoundError
from notaplanet.items.models import Item, ItemsModel
from notaplanet.seasons.models import Episode as SeasonsEpisode
from notaplanet.seasons.models import Season as SeasonsSeason
from notaplanet.seasons.models import SeasonsModel

from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, PartialGAPIJSON
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client

# A movie has no seasons of its own so its single season is given a fixed number.
_MOVIE_SEASON_NUMBER = 0


@cache
def notaplanet() -> NotAPlanet:
    return NotAPlanet(get_around_client=get_around_client())


class ItemsFile(PartialGAPIJSON[ItemsModel]):
    """Items file."""

    API_ENDPOINT = notaplanet().items

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ItemNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid item_id {self.unique_identifier}"

    @override
    def _get(self) -> ItemsModel:
        return self.API_ENDPOINT.download_and_parse([self.unique_identifier])


class SeasonsFile(GAPIJSON[SeasonsModel]):
    """Seasons file."""

    API_ENDPOINT = notaplanet().seasons

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


class FileMixin(MediaTypeMixin, TMDBMixin, register=False):
    def items_file(self, item_id: str) -> ItemsFile:
        """Contains the metadata of a single on-demand movie."""
        return self._file(ItemsFile, item_id)

    def seasons_file(self, series_id: str) -> SeasonsFile:
        """Contains a series' metadata, its seasons, and all of their episodes."""
        return self._file(SeasonsFile, series_id)

    def _item(self, show_key: str) -> Item:
        return self.items_file(show_key).parsed().items[0]

    def _series(self, show_key: str) -> SeasonsModel:
        return self.seasons_file(show_key).parsed()

    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)
        return self._media_type_value == "movie"

    def _seasons(self, show_key: str) -> list[SeasonsSeason]:
        return self._series(show_key).seasons

    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[SeasonsEpisode]:
        for season in self._seasons(show_key):
            if season.number == season_number:
                return season.episodes
        return []

    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single file keyed by the show, but the
        base plugin resolves episode files from a season key alone, so the show
        key is carried inside it.
        """
        return f"{show_key}:{season_number}"

    @classmethod
    def _movie_season_key(cls, show_key: str) -> str:
        return cls._season_key(show_key, _MOVIE_SEASON_NUMBER)

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.partition(":")
        return show_key, int(season_number)

    def _show_file(self, show_key: str) -> BaseFile[Any]:
        if self._is_movie():
            return self.items_file(show_key)
        return self.seasons_file(show_key)

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self._show_file(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            [self._show_file(show_key)],
            season_key,
            show_key,
        )

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file(
            [self._show_file(show_key)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._movie_season_key(show_key)]
        return [
            self._season_key(show_key, season.number)
            for season in self._seasons(show_key)
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode.field_id
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
