# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.episodes import models as episodes_models
from chirashi.exceptions import HTTPError
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_plugin import BasePlugin, JSONFile
from app.plugins.plugins.utils.ip_validator import check_ip_not_matches
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


@cache
def chirashi_client() -> Chirashi:
    return Chirashi()


class Series(JSONFile[series_models.Series]):
    def __init__(self, db: Session, plugin: Plugin, show_key: str) -> None:
        self.__show_key = show_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_key

    def _download(self) -> None:
        with self._log_download(self.__show_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            series = chirashi_client().series
            try:
                response = series.get(self.__show_key)
                content = series.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid URL.
            except HTTPError as e:
                if str(e) != "Unexpected response status code: 404":
                    raise

                self._write(None)

    @override
    def _parse(self, raw: Any) -> series_models.Series:
        return chirashi_client().series.parse(raw)


class Seasons(JSONFile[seasons_models.Seasons]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        show_key: str,
    ) -> None:
        self.__show_key = show_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_key

    def _download(self) -> None:
        with self._log_download(self.__show_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            seasons = chirashi_client().seasons
            response = seasons.get(self.__show_key)
            content = seasons.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> seasons_models.Seasons:
        return chirashi_client().seasons.parse(raw)


class Episodes(JSONFile[episodes_models.Episodes]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        season_key: str,
    ) -> None:
        self.__season_key = season_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_key

    def _download(self) -> None:
        with self._log_download(self.__season_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            episodes = chirashi_client().episodes
            response = episodes.get(self.__season_key)
            content = episodes.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> episodes_models.Episodes:
        return chirashi_client().episodes.parse(raw)


class Browse(JSONFile[list[browse_series_models.Datum]]):
    IMMUTABLE: bool = True

    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        last_update_datetime: datetime,
    ) -> None:
        self._last_update_datetime = last_update_datetime
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._last_update_datetime)

    def _download(self) -> None:
        with self._log_download(str(self._last_update_datetime)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            browse_series = chirashi_client().browse_series
            response = browse_series.get_since_datetime(
                end_datetime=self._last_update_datetime,
            )
            content = browse_series.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[browse_series_models.Datum]:
        parsed_pages = [chirashi_client().browse_series.parse(page) for page in raw]
        return chirashi_client().browse_series.extract_entries(parsed_pages)


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        self.__series_cache: dict[str, Series] = {}
        self.__seasons_cache: dict[str, Seasons] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Wrappers

    def _series_file(self, show_key: str) -> Series:
        return self._get_cached_file(
            self.__series_cache,
            show_key,
            lambda: Series(self.db, self.plugin, show_key),
        )

    def _seasons_file(self, show_key: str) -> Seasons:
        return self._get_cached_file(
            self.__seasons_cache,
            show_key,
            lambda: Seasons(self.db, self.plugin, show_key),
        )

    def _episodes_file(self, season_key: str) -> Episodes:
        return Episodes(self.db, self.plugin, season_key)

    def _browse_file(self, key: datetime | str) -> Browse:
        if isinstance(key, str):
            identifier = Browse.file_key_to_unique_identifier(key)
            key = tz_datetime.fromisotimestamp(identifier)
        return Browse(self.db, self.plugin, key)

    # endregion File Wrappers

    # region File Groups

    @override
    def _show_files(self, show_key: str) -> Sequence[Series | Seasons]:
        return [
            # Required to detect changes to the show.
            self._series_file(show_key),
            # Required to detect new seasons.
            self._seasons_file(show_key),
        ]

    @override
    def _season_files(self, season_key: str) -> Sequence[Seasons | Episodes]:
        return [
            # Required to detect new episodes.
            self._episodes_file(season_key),
        ]

    @override
    def _episode_files(self, season_key: str) -> Sequence[Episodes]:
        # Required to detect changes to the episode.
        return [self._episodes_file(season_key)]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_key: str) -> datetime:
        return super()._show_timestamp(show_key)

    def _season_timestamp(self, season_key: str) -> datetime:
        return super()._season_timestamp(season_key)

    def _episode_timestamp(self, season_key: str) -> datetime:
        return super()._episode_timestamp(season_key)

    # endregion Timestamps

    # region File Data

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return [
            season_data.id for season_data in self._seasons_file(show_key).parsed().data
        ]

    @override
    def _video_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        # Crunchyroll episode files are keyed by season, so episode-level IDs
        # are season IDs for the purposes of the download chain.
        if isinstance(season_keys, str):
            return [season_keys]
        return list(season_keys)

    # endregion File Data

    # region Preload

    @override
    def _preload_show_files(self, show_key: str) -> Sequence[File]:
        statement = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        Series.file_key(show_key),
                        Seasons.file_key(show_key),
                    ],
                ),
            )
        )
        return self.db.exec(statement).all()

    @override
    def _preload_season_files(self, season_keys: list[str]) -> Sequence[File]:
        keys = [Episodes.file_key(sid) for sid in season_keys]
        statement = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(keys))
        )
        return self.db.exec(statement).all()

    @override
    def _preload_episode_files(self, episode_keys: list[str]) -> Sequence[File]:
        keys = [Episodes.file_key(eid) for eid in episode_keys]
        statement = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(keys))
        )
        return self.db.exec(statement).all()

    def _preload_show_season_episode_files(self, show_key: str) -> None:
        self._preload_show_files(show_key)

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

    # endregion Preload
