# TODO: Validate
# This plugin intentionally does not support movies because there are only like 10
# movies on Crunchyroll because the movies page is basically deprecated. All new movies
# appear to be added as a series, for example:
# https://www.crunchyroll.com/series/GMTE00335490/spy-x-family-code-white
# For a full list of unsupported movies see:
# https://www.crunchyroll.com/videos/alphabetical?media=movies

import json
import re
from datetime import date, datetime, timedelta
from functools import cache
from typing import override

from loguru import logger
from sqlmodel import Session, col, select

from app.media.models import Episode, EpisodeWatch, File, Season, Show, Source
from app.media.schemas import (
    EpisodeInput,
    SeasonInput,
    ShowInput,
    SourceInput,
    WatchImportEntry,
    WatchImportFormatInformation,
    WatchImportResult,
)
from app.plugins.Crunchyroll.files import Browse, FileMixin
from app.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.users.models import User
from app.utils import tz_datetime


class Crunchyroll(FileMixin, register=True):
    # region Initialization

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
        """Initialize CrunchyRoll plugin."""
        self.__latest_browse_file_value: Browse | None = None
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # endregion

    # region Watch Import

    @classmethod
    @override
    def import_watch_history_info(cls) -> WatchImportFormatInformation:
        return WatchImportFormatInformation(
            plugin_id=cls.plugin_id(),
            plugin_name=cls._plugin_name(),
            file_type="JSON",
            file_extension=".json",
            instructions=(
                "1. Use [Itamae](https://github.com/ryn-cx/itamae) to download "
                "your Crunchyroll watch history\n"
                "2. Upload the file here"
            ),
        )

    @override
    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResult:
        """Import Crunchyroll watch history from Itamae JSON export."""
        entries = json.loads(content)

        entry_episode_ids: list[str] = [entry["id"] for entry in entries]

        episodes_on_database = self._get_episodes_by_id(entry_episode_ids)
        watched_episode_dates = self._get_watched_episode_dates(
            user,
            episodes_on_database,
        )

        added_watches: list[WatchImportEntry] = []
        skipped_watches: list[WatchImportEntry] = []
        existing_watches: list[WatchImportEntry] = []

        for entry, episode_id in zip(entries, entry_episode_ids, strict=True):
            panel = entry["panel"]
            episode_metadata = panel["episode_metadata"]

            import_entry = WatchImportEntry(
                show=episode_metadata["series_title"],
                show_url=self.__show_url(episode_metadata["series_id"]),
                episode=panel["title"],
                episode_url=self.__episode_url(episode_id),
            )

            if not (episode := episodes_on_database.get(episode_id)):
                skipped_watches.append(import_entry)
                continue

            watch_date = tz_datetime.fromisotimestamp(entry["date_played"])

            watched_dates = watched_episode_dates.setdefault(str(episode.id), [])
            if new_only and watched_dates:
                existing_watches.append(import_entry)
                continue

            if watch_date in watched_dates:
                existing_watches.append(import_entry)
                continue

            self.db.add(
                EpisodeWatch(
                    user_id=user.id,
                    episode_id=episode.id,
                    watch_date=watch_date,
                    verified=verified,
                ),
            )
            watched_dates.append(watch_date)
            added_watches.append(import_entry)

        return WatchImportResult(
            added=added_watches,
            existing=existing_watches,
            skipped=skipped_watches,
        )

    # endregion Watch Import

    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        if match := re.match(self._url_regex(), url):
            self._show_id = match.group("show_id")
            show = self._preload_show(preload_sources=True, preload_episodes=True)
            if not show:
                self._preload_show_season_episode_files()
                self.__validate_show_id(url)
                self._download_initial_files()
                show = self.__upsert_source()

            return [URLImportResult(show=show, whitelist_mode=False)]

        msg = f"Invalid {self._plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    def __validate_show_id(self, url: str) -> None:
        series_json = self._series_file(self._show_id)
        self._is_valid_url(series_json, url)

    # region Update Source

    @override
    def update_source(self, source: Source) -> None:
        self.__download_new_browse_json(source)
        self.__process_new_browse_files(source)
        SourceInput(
            key=self._plugin_name(),
            name=self._plugin_name(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=f"{self._base_url()}build/assets/img/favicons/favicon-v2-96x96.png",
            # Check for new data daily.
            update_at=self._latest_browse_file.get_file_data_timestamp()
            + timedelta(days=1),
            data_timestamp=self._latest_browse_file.get_file_data_timestamp(),
        ).upsert(self.plugin, source)

    def __download_new_browse_json(self, source: Source) -> None:
        # Only update the file if the last update was over a day ago. This stops a
        # failed download from repeating indefinitely.
        browse_download_date = self._latest_browse_file.get_file_data_timestamp()
        minimum_timestamp = browse_download_date + timedelta(days=1)
        if minimum_timestamp > tz_datetime.now():
            return

        # Use data_timestamp as the key so this import will download everything up
        # to the last import because data_timestamp represents when the file was
        # written and the key represents the end_datetime used to generate the file.
        last_completion = self._latest_browse_file.get_file_data_timestamp()
        browse_json = self._browse_file(last_completion)
        browse_json.download_if_outdated(source.update_at)

    def __process_new_browse_files(self, source: Source) -> None:
        """Import existing browse files that have not been imported yet."""
        # B018 - This preloads the shows into memory so Show.get_from_memory can be used
        # to find outdated shows when processing the browse files.
        source.shows  # noqa: B018

        for browse_json in self.__get_new_browse_files_from_db():
            self._latest_browse_file = browse_json
            for release in browse_json.parsed():
                if show := Show.get_from_memory(self.db, source, release.id):
                    # last_public appears to represent the last time a public change was
                    # made to the show's data.
                    # Both show and season need to be set to be updated because the
                    # season will detect new episodes for existing seasons and the shows
                    # will detect episodes for new seasons.
                    show.set_update_at(release.last_public)
                    # There is no way to detect what season the update is for so update
                    # all of the seasons.
                    for season in show.seasons:
                        season.set_update_at(release.last_public)
            browse_json.set_file_extra("Imported")

    def __get_new_browse_files_from_db(self) -> list[Browse]:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Browse.__name__}/"),
                col(File.extra).is_(None),
            )
            .order_by(col(File.data_timestamp).asc())
        )
        return [
            self.__db_file_to_browse_json(browse_file)
            for browse_file in self.db.exec(statement)
        ]

    # endregion

    # region Update Media

    @override
    def update_show(self, show: Show) -> None:
        self._show_id = show.key
        self.__preload_update_media()
        for show_file in self._show_files(show.key):
            show_file.download_if_outdated(show.update_at)
        self.__upsert_source()

    @override
    def update_season(self, season: Season) -> None:
        self._show_id = season.show.key
        self.__preload_update_media()
        for season_file in self._season_files(season.show.key, season.key):
            season_file.download_if_outdated(season.update_at)
        self.__upsert_source()

    @override
    def update_episode(self, episode: Episode) -> None:
        self._show_id = episode.season.show.key
        self.__preload_update_media()
        for episode_file in self._episode_files(episode.season.key):
            episode_file.download_if_outdated(episode.update_at)
        self.__upsert_source()

    def __preload_update_media(self) -> None:
        self._preload_show(preload_episodes=True)
        self._preload_show_season_episode_files()

    # endregion

    # region URL

    @classmethod
    @cache
    @override
    def domains(cls) -> list[str]:
        return ["crunchyroll.com"]

    @classmethod
    @cache
    def __show_url(cls, show_id: str) -> str:
        return f"{cls._base_url()}series/{show_id}"

    @classmethod
    @cache
    def __episode_url(cls, episode_id: str) -> str:
        return f"{cls._base_url()}watch/{episode_id}"

    @classmethod
    @cache
    @override
    def _url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URLs:
        #   Click on any link to a series from the main page:
        #       https://www.crunchyroll.com/series/GMEHME7GX/turkey-time-to-strike
        regex_string = r"\/series\/(?P<show_id>[A-Z0-9]{9,})(?:\/|$)"
        return domain_regex + regex_string

    # endregion

    # region Getters and Setters
    @property
    def _latest_browse_file(self) -> Browse:
        """Get the _latest_browse_file, raises AttributeError if not available."""
        if not self.__latest_browse_file_value:
            if file := self._preload_latest_browse_file():
                self.__latest_browse_file_value = self.__db_file_to_browse_json(file)
            else:
                self.__latest_browse_file_value = self._browse_file(tz_datetime.now())
        return self.__latest_browse_file_value

    @_latest_browse_file.setter
    def _latest_browse_file(self, new_value: Browse) -> None:
        self.__latest_browse_file_value = new_value

    # endregion

    # region Upsert

    def __upsert_source(self) -> Show:
        logger.info(f"Upserting show: {self._pretty_show_name()}")
        source = Source.get_from_memory(self.db, self.plugin, self._plugin_name())
        source = SourceInput(
            key=self._plugin_name(),
            name=self._plugin_name(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=f"{self._base_url()}build/assets/img/favicons/favicon-v2-96x96.png",
            # Check for new data daily.
            update_at=self._latest_browse_file.get_file_data_timestamp()
            + timedelta(days=1),
            data_timestamp=self._latest_browse_file.get_file_data_timestamp(),
        ).upsert(self.plugin, source)
        return self.__upsert_show(source)

    def __upsert_show(self, source: Source) -> Show:
        # Soft delete everything then re-import everything to manage deleted entries.
        if existing_show := Show.get_from_memory(self.db, source, self._show_id):
            existing_show.soft_delete()

        series_file = self._series_file(self._show_id)
        series_data = series_file.parsed().data[0]

        show = ShowInput(
            key=series_data.id,
            name=series_data.title,
            # This isn't technically a TV Series or Movie because Crunchyroll mixes them
            # together. "Anime Series" is good enough for the majority of entries even
            # though Crunchyroll does have some live action content.
            media_type="Anime Series",
            description=series_data.description,
            url=self.__show_url(series_data.id),
            data_timestamp=self._show_timestamp(series_data.id),
        ).upsert(source, existing_show)
        self.__upsert_seasons(show)
        self.__set_season_update_at_using_episode_release_date(show)
        return show

    def __upsert_seasons(self, show: Show) -> None:
        seasons_file = self._seasons_file(self._show_id)
        seasons_data = seasons_file.parsed().data
        season_data_dict = {season_data.id: season_data for season_data in seasons_data}
        season_dict_lookup = {season.key: season for season in show.seasons}

        seasons: list[Season] = []
        for i, season_id in enumerate(self._season_ids_from_file):
            season_data = season_data_dict[season_id]

            seasons.append(
                SeasonInput(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=self._season_timestamp(show.key, season_id),
                ).upsert(show, season_dict_lookup.get(season_data.id)),
            )
        self.__upsert_episodes(seasons)

    def __upsert_episodes(self, seasons: list[Season]) -> None:
        for season in seasons:
            episodes_file = self._episodes_file(season.key)
            episodes_data = episodes_file.parsed()
            episode_dict_lookup = {episode.key: episode for episode in season.episodes}
            for i, episode_data in enumerate(episodes_data.data):
                EpisodeInput(
                    key=episode_data.id,
                    url=self.__episode_url(episode_data.id),
                    sort_order=i,
                    description=episode_data.description,
                    image_url=episode_data.images.thumbnail[0][-1].source,
                    episode_number=episode_data.episode_number,
                    name=episode_data.title,
                    release_date=episode_data.premium_available_date.date()
                    if episode_data.premium_available_date
                    else None,
                    air_date=episode_data.episode_air_date.date()
                    if episode_data.episode_air_date
                    else None,
                    duration=episode_data.duration_ms // 1000,
                    data_timestamp=self._episode_timestamp(season.key),
                ).upsert(season, episode_dict_lookup.get(episode_data.id))

    def __set_season_update_at_using_episode_release_date(
        self,
        show: Show,
    ) -> None:
        """Sets the season's update_at based on the latest episode release date.

        The date will be set to 7 days after the latest episode's release date if that
        date is newer than the current data_timestamp.
        """
        time_delta: timedelta = timedelta(days=7)
        for season in show.seasons:
            latest_episode = max(
                season.episodes,
                key=lambda ep: ep.release_date or date.min,
            )

            if not (latest_episode and latest_episode.release_date):
                return

            season.set_update_at(
                tz_datetime.combine(
                    latest_episode.release_date + time_delta,
                    datetime.min.time(),
                ),
            )

    # endregion

    # region Helpers

    def __db_file_to_browse_json(self, file: File) -> Browse:
        file_id_str = Browse.file_key_to_unique_identifier(file.key)
        file_id_date = tz_datetime.fromisotimestamp(file_id_str)
        return self._browse_file(file_id_date)

    # endregion
