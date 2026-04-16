# TODO: Add search support.
# This plugin intentionally does not support movies from the movies page because it has
# been unofficially deprecated as movies are now added as a series instead.

# New movie format example:
# https://www.crunchyroll.com/series/GMTE00335490/spy-x-family-code-white
# Old movie page:
# https://www.crunchyroll.com/videos/alphabetical?media=movies

import json
import re
from datetime import timedelta
from typing import override

from loguru import logger
from sqlmodel import col, select

from app.plugins.models import File
from app.plugins.plugins.Crunchyroll.files import Browse
from app.plugins.plugins.Crunchyroll.upsert import UpsertMixin
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.plugins.plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
    WatchHistoryMixin,
)
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult


class Crunchyroll(WatchHistoryMixin, UpsertMixin, register=True):
    _VERSION = "0.0.1"
    import_watch_history_file_extension = ".json"

    @override
    def initialize_plugin(self) -> None:
        super().initialize_plugin()
        if not Source.get_from_memory(self.session, self.plugin, self.plugin_key()):
            latest_browse_file = self._get_latest_browse_file()
            self._upsert_source(latest_browse_file)

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.crunchyroll.com/series/G4PH0WXVJ/spy-x-family`\n\n"
        )

    # region Watch Import

    @classmethod
    @override
    def import_watch_history_instructions(cls) -> str:
        return (
            "1. Use [Itamae](https://github.com/ryn-cx/itamae) to download "
            "your Crunchyroll watch history\n"
            "2. Upload the file here"
        )

    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        entries = json.loads(content)
        parsed_entries: list[ParsedWatchEntry] = []
        for entry in entries:
            episode_key = entry["id"]
            panel = entry["panel"]
            episode_metadata = panel["episode_metadata"]
            parsed_entries.append(
                ParsedWatchEntry(
                    episode_key=episode_key,
                    watch_date=tz_datetime.fromisoformat(entry["date_played"]),
                    import_result=WatchImportResult(
                        show=episode_metadata["series_title"],
                        show_url=self._show_url(episode_metadata["series_id"]),
                        episode=panel["title"],
                        episode_url=self._episode_url(episode_key),
                    ),
                ),
            )
        return parsed_entries

    # endregion Watch Import

    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key = self.parse_url(url)
        self._validate_url(show_key, url)
        show = self._import_show(show_key)
        return [URLImportResult(show=show, whitelist_mode=False)]

    @classmethod
    @override
    def parse_url(cls, url: str) -> str:
        if match := re.match(cls._url_regex(), url):
            return match.group("show_key")

        msg = f"Invalid {cls.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, show_key: str, url: str) -> None:
        series_json = self._series_file(show_key)
        series_json.download_if_outdated()
        self.raise_invalid_url_if_no_content(series_json, url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key=show_key).one_or_none():
            return show

        _cache = self._download_show_files(show_key)
        source = Source.get_one_from_memory(
            self.session,
            self.plugin,
            self.plugin_key(),
        )
        return self._upsert_show(source, show_key=show_key)

    # endregion Import URL

    # region Update Source

    @override
    def update_source(self, source: Source) -> None:
        latest_browse_file = self._get_latest_browse_file()
        latest_browse_file = self._download_new_browse_json(source, latest_browse_file)
        self._process_new_browse_files(source)
        self._upsert_source(latest_browse_file)

    def _download_new_browse_json(self, source: Source, browse: Browse) -> Browse:
        # Only download a Browse file at most once a day. This will protect against a
        # failed source update downloading a Browse file over and over again.
        browse_download_date = browse.database_record.data_timestamp
        minimum_timestamp = browse_download_date + timedelta(days=1)
        if minimum_timestamp > tz_datetime.now():
            return browse

        # Use data_timestamp as the key so this import will download everything up
        # to the last import because data_timestamp represents when the file was
        # written and the key represents the end_datetime used to generate the file.
        new_browse = self._browse_file(browse.database_record.data_timestamp)
        new_browse.download_if_outdated(source.update_at)
        return new_browse

    def _process_new_browse_files(self, source: Source) -> None:
        """Import existing browse files that have not been imported yet."""
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self._get_new_browse_files_from_db(source):
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            for release in browse_json.datums():
                if show := Show.get_from_memory(self.session, source, release.id):
                    logger.info("Matched show: {}", show.name or release.id)
                    # last_public appears to represent the last time a public change
                    # was made to the show's data. There is no way to detect what
                    # season the update is for so both show and season need to be set
                    # to be updated because the season will detect new episodes for
                    # existing seasons and the shows will detect episodes for new
                    # seasons.
                    show.set_update_at(release.last_public)
                    for season in show.seasons:
                        season.set_update_at(release.last_public)

    def _get_new_browse_files_from_db(self, source: Source) -> list[Browse]:
        data_timestamp = source.data_timestamp or tz_datetime.fromtimestamp(0)

        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Browse.__name__}/"),
                col(File.data_timestamp) > data_timestamp,
            )
            .order_by(col(File.data_timestamp).asc())
        )
        browse_files = self.session.exec(statement)
        return [self._browse_file(browse_file) for browse_file in browse_files]

    # endregion

    # region URL

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["crunchyroll.com"]

    @classmethod
    @override
    def _url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        # Example URLs:
        #   https://www.crunchyroll.com/series/GRMG8ZQZR/one-piece
        regex_string = r"\/series\/(?P<show_key>[A-Z0-9]{9,})(?:\/|$)"
        return domain_regex + regex_string
