from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.episodes import models as episodes_models
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models
from sqlmodel import col, select

from app.config import settings
from app.plugins.models import File
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON
from app.utils import tz_datetime


@cache
def chirashi_client() -> Chirashi:
    return Chirashi(
        get_around_server=settings.GET_AROUND_SERVER,
        get_around_password=settings.GET_AROUND_PASSWORD,
    )


class Series(GAPIJSON[series_models.Series]):
    # Occurs when a user puts in an invalid URL.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = chirashi_client().series


class Seasons(GAPIJSON[seasons_models.Seasons]):
    api_endpoint = chirashi_client().seasons


class Episodes(GAPIJSON[episodes_models.Episodes]):
    api_endpoint = chirashi_client().episodes


class Browse(GAPIListJSON[browse_series_models.BrowseSeries]):
    IMMUTABLE = True
    api_endpoint = chirashi_client().browse_series

    # Requires specific named parameters
    @override
    def _get(self) -> list[browse_series_models.BrowseSeries]:
        # TODO: Why does this use tz_datetime but JustWatch has to use datetime
        return chirashi_client().browse_series.get_since_datetime(
            end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
        )

    def datums(self) -> list[browse_series_models.Datum]:
        """Flatten all pages into a single list of datum entries."""
        return chirashi_client().browse_series.extract_entries(self.parsed())


class FileMixin(BasePlugin, register=False):
    # region File Wrappers

    def _series_file(self, show_key: str) -> Series:
        return self._get_weakref_cached_file(
            Series,
            show_key,
            lambda: Series(self.db, self.plugin, show_key),
        )

    def _seasons_file(self, show_key: str) -> Seasons:
        return self._get_weakref_cached_file(
            Seasons,
            show_key,
            lambda: Seasons(self.db, self.plugin, show_key),
        )

    def _episodes_file(self, season_key: str) -> Episodes:
        return self._get_weakref_cached_file(
            Episodes,
            season_key,
            lambda: Episodes(self.db, self.plugin, season_key),
        )

    def _browse_file(self, browse_datetime: datetime | File) -> Browse:
        if isinstance(browse_datetime, File):
            str_datetime = Browse.file_key_to_unique_identifier(browse_datetime.key)
        else:
            str_datetime = str(browse_datetime)
        return self._get_weakref_cached_file(
            Browse,
            str_datetime,
            lambda: Browse(self.db, self.plugin, str_datetime),
        )

    # endregion File Wrappers

    # region File Groups

    @override
    def _show_files(self, show_key: str, **kwargs: Any) -> Sequence[Series | Seasons]:
        return [
            # Required to detect new seasons.
            self._seasons_file(show_key),
            # Required to detect changes to the show.
            self._series_file(show_key),
        ]

    @override
    def _season_files(  # type: ignore[override]
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[Seasons | Episodes]:
        return [
            # Required to detect new episodes.
            self._episodes_file(season_key),
            # Required to detect changes to the season.
            self._seasons_file(show_key),
        ]

    @override
    def _episode_files(self, season_key: str, **kwargs: Any) -> Sequence[Episodes]:  # type: ignore[override]
        # Required to detect changes to the episode.
        return [self._episodes_file(season_key)]

    # endregion File Groups

    # region File Data

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return [
            season_data.id for season_data in self._seasons_file(show_key).parsed().data
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.id
            for season_key in season_keys
            for episode in self._episodes_file(season_key).parsed().data
        ]

    # endregion File Data

    def _preload_latest_browse_file(self) -> File | None:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Browse.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self.db.exec(statement).first()

    def _get_latest_browse_file(self) -> Browse:
        if file := self._preload_latest_browse_file():
            return self._browse_file(file)
        browse = self._browse_file(tz_datetime.now())
        browse.download_if_outdated()
        return browse
