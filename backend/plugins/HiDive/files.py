# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import override

from diving_board import DivingBoard
from diving_board.playlist import models as playlist_models
from diving_board.schedule import models as schedule_models
from diving_board.search import models as search_models
from diving_board.season import models as season_models
from diving_board.series import models as series_models
from diving_board.vod import models as vod_models
from sqlmodel import Session, col, select

from app.config import settings
from app.plugins.models import File, Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    GAPIListJSON,
    PartialGAPIJSON,
)


@cache
def diving_board() -> DivingBoard:
    server: str | None = settings.GET_AROUND_SERVER
    if server == "changethis":
        server = None
    password: str | None = settings.GET_AROUND_PASSWORD
    if password == "changethis":  # noqa: S105
        password = None
    return DivingBoard(get_around_server=server, get_around_password=password)


class Season(PartialGAPIJSON[season_models.SeasonModel]):
    # Occurs when the user imports an invalid TV show url.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = diving_board().season

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> season_models.SeasonModel:
        return diving_board().season.get(int(self.unique_identifier))


class Vod(PartialGAPIJSON[vod_models.VodModel]):
    api_endpoint = diving_board().vod

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> vod_models.VodModel:
        return diving_board().vod.get(int(self.unique_identifier))


class Playlist(PartialGAPIJSON[playlist_models.PlaylistModel]):
    # Occurs when the user imports an invalid movie url.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = diving_board().playlist

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> playlist_models.PlaylistModel:
        return diving_board().playlist.get(int(self.unique_identifier))


class Series(PartialGAPIJSON[series_models.SeriesModel]):
    # Occurs when the user imports an invalid series url.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = diving_board().series

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> series_models.SeriesModel:
        return diving_board().series.get(int(self.unique_identifier))


class Schedule(GAPIListJSON[schedule_models.ScheduleModel]):
    api_endpoint = diving_board().schedule

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        input_date: datetime,
    ) -> None:
        self.input_date = input_date
        super().__init__(session, plugin, input_date.isoformat())

    @override
    def _get(self) -> list[schedule_models.ScheduleModel]:
        # Start at the first of the month because it matches the normal API calls.
        from_ = self.input_date.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return diving_board().schedule.get_until_datetime(
            from_=from_,
            end_datetime=tz_datetime.now(),
        )


class Search(GAPIJSON[search_models.SearchModel]):
    api_endpoint = diving_board().search


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._media_type_value: str | None = None

    @property
    def _media_type(self) -> str:
        if self._media_type_value is None:
            msg = "Media type has not been set."
            raise AttributeError(msg)
        return self._media_type_value

    def season_file(self, season_key: str | int) -> Season:
        """Return a cached season file for the given season key."""
        key = str(season_key)
        return self._get_cached_file(
            Season,
            key,
            lambda: Season(self.session, self.plugin, key),
        )

    def vod_file(self, vod_key: str | int) -> Vod:
        """Return a cached vod file for the given vod key."""
        key = str(vod_key)
        return self._get_cached_file(
            Vod,
            key,
            lambda: Vod(self.session, self.plugin, key),
        )

    def playlist_file(self, playlist_key: str | int) -> Playlist:
        """Return a cached playlist file for the given playlist key."""
        key = str(playlist_key)
        return self._get_cached_file(
            Playlist,
            key,
            lambda: Playlist(self.session, self.plugin, key),
        )

    def series_file(self, series_key: str | int) -> Series:
        """Return a cached series file for the given series key."""
        key = str(series_key)
        return self._get_cached_file(
            Series,
            key,
            lambda: Series(self.session, self.plugin, key),
        )

    def schedule_file(self, input_date: datetime | File) -> Schedule:
        """Return a cached schedule file for the given datetime or existing File."""
        if isinstance(input_date, File):
            input_date = datetime.fromisoformat(
                Schedule.file_key_to_unique_identifier(input_date.key),
            )
        return self._get_cached_file(
            Schedule,
            input_date,
            lambda: Schedule(self.session, self.plugin, input_date),
        )

    def search_file(self, query: str) -> Search:
        """Return a cached search file for the given query."""
        return self._get_cached_file(
            Search,
            query,
            lambda: Search(self.session, self.plugin, query),
        )

    def preload_latest_schedule_file(self) -> File | None:
        """Return the most recent schedule File from the database, or None."""
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Schedule.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self.session.exec(statement).first()

    def get_latest_schedule_file(self) -> Schedule:
        """Return the latest schedule file, downloading a fresh one if none exist."""
        if file := self.preload_latest_schedule_file():
            return self.schedule_file(file)
        schedule = self.schedule_file(tz_datetime.now())
        schedule.download_if_outdated()
        return schedule

    @override
    def _show_files(
        self,
        show_key: str,
    ) -> Sequence[Season | Series | Playlist]:
        if self._media_type == "Movie":
            return [self.playlist_file(show_key)]
        return [self.series_file(show_key)]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[Season | Playlist]:
        if self._media_type == "Movie":
            return [self.playlist_file(season_key)]
        return [
            # Required to detect new episodes and changes to the season.
            self.season_file(season_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[Season | Vod | Playlist]:
        if self._media_type == "Movie":
            return [
                self.playlist_file(show_key),
                self.vod_file(episode_key),
            ]
        return [
            # Required to detect changes to the episode information.
            self.vod_file(episode_key),
            self.season_file(season_key),
        ]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        # TODO: Is this seperate check needed?
        if self._media_type == "Movie":
            return [show_key]
        series_data = self.series_file(show_key).parsed()
        return [str(item.id) for item in self._series_season_items(series_data)]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if self._media_type == "Movie":
                playlist_data = self.playlist_file(season_key).parsed()
                bucket = diving_board().playlist.extract_bucket_playlist(
                    playlist_data,
                )
                episode_keys.extend(str(item.id) for item in bucket.attributes.items)
                continue
            season_data = self.season_file(season_key).parsed()
            bucket = diving_board().season.extract_bucket_season(season_data)
            episode_keys.extend(str(item.id) for item in bucket.attributes.items)
        return episode_keys

    @staticmethod
    def _series_season_items(
        series_data: series_models.SeriesModel,
    ) -> list[series_models.Item1]:
        """Return the list of seasons from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.seasons:
                return element.attributes.seasons.items
        msg = "No seasons element found in series file."
        raise ValueError(msg)

    @staticmethod
    def _series_image_url(series_data: series_models.SeriesModel) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.image:
                return element.attributes.image.attributes.source
        msg = "No image element found in series file."
        raise ValueError(msg)
