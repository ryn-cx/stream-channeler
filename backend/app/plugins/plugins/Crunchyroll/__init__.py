# TODO: Validate
# This plugin intentionally does not support movies because there are only like 10
# movies on Crunchyroll because the movies page is basically deprecated. All new movies
# appear to be added as a series, for example:
# https://www.crunchyroll.com/series/GMTE00335490/spy-x-family-code-white
# For a full list of unsupported movies see:
# https://www.crunchyroll.com/videos/alphabetical?media=movies

import re
from datetime import timedelta
from functools import cache
from typing import override

from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import File
from app.plugins.plugins.Crunchyroll.files import Browse
from app.plugins.plugins.Crunchyroll.watch import WatchMixin
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


class Crunchyroll(WatchMixin, register=True):
    _VERSION = "0.0.1"

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

    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        if match := re.match(self._url_regex(), url):
            show_key = match.group("show_key")
            show = self._preload_show(
                show_key=show_key,
                preload_source=True,
                preload_episodes=True,
            ).one_or_none()
            if not show:
                self._preload_show_season_episode_files(show_key)
                self.__validate_show_key(show_key, url)
                self._download_initial_files(show_key)
                source = self._upsert_source(show_key)
                show = Show.get_one(self.db, source, show_key)

            return [URLImportResult(show=show, whitelist_mode=False)]

        msg = f"Invalid {self._plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    def __validate_show_key(self, show_key: str, url: str) -> None:
        series_json = self._series_file(show_key)
        series_json.download_if_outdated()
        self.raise_if_no_content(series_json, url)

    # endregion

    # region Update Source

    @override
    def update_source(self, source: Source) -> None:
        self.__download_new_browse_json(source)
        self.__process_new_browse_files(source)
        self._upsert_source(source.shows[0].key if source.shows else "")

    def __download_new_browse_json(self, source: Source) -> None:
        # Only update the file if the last update was over a day ago. This stops a
        # failed download from repeating indefinitely.
        browse_download_date = self._latest_browse_file.get_data_timestamp()
        minimum_timestamp = browse_download_date + timedelta(days=1)
        if minimum_timestamp > tz_datetime.now():
            return

        # Use data_timestamp as the key so this import will download everything up
        # to the last import because data_timestamp represents when the file was
        # written and the key represents the end_datetime used to generate the file.
        last_completion = self._latest_browse_file.get_data_timestamp()
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
            self._browse_file(browse_file.key)
            for browse_file in self.db.exec(statement)
        ]

    # endregion

    # region Update

    @override
    def update_episode(self, episode: Episode) -> None:
        # Override because Crunchyroll episode files are keyed by season, not episode.
        _cache = self._download_episode_files(episode.season.key, episode.update_at)
        self._upsert_episode(episode.season, episode.key)

    # endregion

    # region URL

    @classmethod
    @cache
    @override
    def domains(cls) -> list[str]:
        return ["crunchyroll.com"]

    @classmethod
    @cache
    def _show_url(cls, show_key: str) -> str:
        return f"{cls._base_url()}series/{show_key}"

    @classmethod
    @cache
    def _episode_url(cls, episode_key: str) -> str:
        return f"{cls._base_url()}watch/{episode_key}"

    @classmethod
    @cache
    @override
    def _url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URLs:
        #   Click on any link to a series from the main page:
        #       https://www.crunchyroll.com/series/GMEHME7GX/turkey-time-to-strike
        regex_string = r"\/series\/(?P<show_key>[A-Z0-9]{9,})(?:\/|$)"
        return domain_regex + regex_string

    # endregion

    # region Getters and Setters

    @property
    def _latest_browse_file(self) -> Browse:
        """Get the _latest_browse_file, raises AttributeError if not available."""
        if not self.__latest_browse_file_value:
            if file := self._preload_latest_browse_file():
                self.__latest_browse_file_value = self._browse_file(file.key)
            else:
                browse = self._browse_file(tz_datetime.now())
                browse.download_if_outdated()
                self.__latest_browse_file_value = browse
        return self.__latest_browse_file_value

    @_latest_browse_file.setter
    def _latest_browse_file(self, new_value: Browse) -> None:
        self.__latest_browse_file_value = new_value

    # endregion

    # endregion
