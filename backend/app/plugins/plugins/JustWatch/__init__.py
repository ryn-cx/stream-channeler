import json
from collections.abc import Sequence
from datetime import date, timedelta
from difflib import get_close_matches
from typing import Any, override

from loguru import logger
from sqlmodel import col, select

from app.plugins.models import File, Plugin
from app.plugins.plugins.JustWatch.files import (
    NewTitleBucket,
    ProvidersLocale,
)
from app.plugins.plugins.JustWatch.search import SearchMixin
from app.plugins.plugins.JustWatch.upsert import UpsertMixin
from app.plugins.plugins.utils.abstract_plugin import URLImportResult
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import strict_re


class JustWatch(SearchMixin, UpsertMixin, register=True):
    _VERSION = "0.0.1"

    @override
    def initialize_plugin(self) -> None:
        super().initialize_plugin()
        if self.plugin.data_timestamp is None:
            providers_file = self._providers_locale_file()
            providers_file.download_if_outdated()

            self._upsert_sources(providers_file)

            bucket = self._new_titles_bucket_file(
                providers_file.database_entry.data_timestamp,
            )
            bucket.download_if_outdated()

            self._download_latest_new_titles_bucket()
            latest_bucket = self._get_latest_new_titles_bucket().one()

            self.plugin.data_timestamp = latest_bucket.data_timestamp
            self.plugin.set_update_at(self.plugin.data_timestamp + timedelta(days=1))

    supports_import_url = True

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/TV Show on Hulu]\n"
            "> `Hulu justwatch.com/us/tv-show/breaking-bad`\n\n"
            "> [!TIP/Movie on Netflix]\n"
            "> `Netflix justwatch.com/us/movie/inception`\n\n"
            "> [!WARNING/TV Show on All Websites (may cause duplicates)]\n"
            "> `justwatch.com/us/tv-show/breaking-bad`\n\n"
            "> [!WARNING/Movie on All Websites (may cause duplicates)]\n"
            "> `Netflix justwatch.com/us/movie/inception`\n\n"
        )

    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        match = strict_re.strict_match(self._url_regex(), url)
        source_name = match.group("source_name")
        show_key = match.group("show_key")
        _locale = match.group("locale")  # TODO: Support multiple locales from JustWatch
        season_key = match.group("season_key")

        if not (shows := self._preload_show(show_key=show_key).all()):
            self._validate_show_key(show_key, url)
            _cache = (
                self._download_show_files(show_key),
                self._preload_sources().all(),
            )
            shows = self._upsert_shows(show_key)

        return self._create_url_import_results(shows, source_name, season_key)

    def _validate_show_key(self, show_key: str, url: str) -> None:
        series_json = self._url_title_details_file(show_key)
        series_json.download_if_outdated()
        self.raise_invalid_url_if_no_content(series_json, url)

    def _create_url_import_results(
        self,
        shows: Sequence[Show],
        source_name: str | None,
        season_key: str | None,
    ) -> list[URLImportResult]:
        # If the user specified a source name get the show for that source only,
        # otherwise get all shows.
        filtered_shows = self._get_best_show(shows, source_name)

        # If no season was specified return all shows should be returned.
        if not season_key:
            return [
                URLImportResult(show=show, whitelist_mode=False)
                for show in filtered_shows
            ]

        # If the URL that the user used was for a specific season only return that
        # season. The season.id value in the database is the internal one used by
        # JustWatch, but the user's input will be the external one so the easiest way
        # to match a season is by using the actual season number.
        season_number = int(season_key.split("-")[-1])
        return [
            URLImportResult(show=show, seasons=[season], whitelist_mode=True)
            for show in filtered_shows
            if (
                season := next(
                    s for s in show.seasons if s.season_number == season_number
                )
            )
            and season.episodes
        ]

    def _get_best_show(
        self,
        shows: Sequence[Show],
        source_name: str | None,
    ) -> Sequence[Show]:
        """Filters shows based on the closest match to the given source name.

        Returns:
        - If source_name is None or empty, all shows are returned.
        - If source_name is a valid string, the show with the closest matching name is
        returned.
        """
        if not source_name or not shows:
            return shows

        source_name = source_name.lower()
        sources: dict[str, Show] = {
            show.source.name.lower(): show for show in shows if show.source.name
        }
        best_match = get_close_matches(source_name, sources, n=1, cutoff=0.0)
        return [sources[best_match[0]]]

    # endregion

    # region Update Plugin

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        providers_file = self._providers_locale_file()
        providers_file.download_if_outdated(self.plugin.update_at)
        self._upsert_sources(providers_file)

        _cache = plugin.sources
        self._download_latest_new_titles_bucket()
        self._process_new_titles_buckets()
        latest_bucket = self._get_latest_new_titles_bucket().one()

        plugin.data_timestamp = min(
            latest_bucket.data_timestamp,
            providers_file.database_entry.data_timestamp,
        )
        plugin.set_update_at(plugin.data_timestamp + timedelta(days=1))

    def _process_new_titles_buckets(self) -> None:
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{NewTitleBucket.__name__}/"),
                col(File.data_timestamp) > self.plugin.data_timestamp
                if self.plugin.data_timestamp
                else True,
            )
            .order_by(col(File.data_timestamp).asc())
        )
        for file in self.db.exec(statement).all():
            bucket = self._new_titles_bucket_file(file)
            for edge in bucket.parsed_edges():
                short_name = edge.key.package.short_name
                source = Source.get_from_memory(self.db, self.plugin, short_name)
                if not source:
                    msg = f"Source with key {short_name!r} not found."
                    raise ValueError(msg)

                extra: set[str] = set(json.loads(source.extra or "[]"))
                extra.add(edge.key.date.isoformat())
                source.extra = json.dumps(sorted(extra))
                source.set_update_at(source.modified_at)

    # endregion

    # region Update Source

    @override
    def update_source(self, source: Source) -> None:
        loaded_extra = json.loads(source.extra or "[]")
        dates = [date.fromisoformat(date_str) for date_str in loaded_extra]
        if not dates:
            msg = f"Source {source.key} has no dates to update on its extra field."
            raise ValueError(msg)

        self._download_new_titles_files(source, dates)
        self._process_new_titles_files(source, dates)

        incomplete_dates: list[str] = []
        for new_titles_date in dates:
            new_titles_file = self._new_titles_file(source.key, new_titles_date)
            minimum_timestamp = self.minimum_new_titles_data_timestamp(new_titles_file)
            # The files should be downloaded again at a later date if there is a chance
            # new entries can be added to it in the future.
            if minimum_timestamp > new_titles_file.database_entry.data_timestamp:
                incomplete_dates.append(new_titles_date.isoformat())

        if incomplete_dates:
            source.extra = json.dumps(incomplete_dates)
            _date = date.fromisoformat(incomplete_dates[0])
            earliest_file = self._new_titles_file(source.key, _date)
            minimum_timestamp = self.minimum_new_titles_data_timestamp(earliest_file)
            source.set_update_at(minimum_timestamp)
        else:
            source.extra = None
            source.update_at = None

        source.data_timestamp = max(
            self._new_titles_file(
                source.key,
                new_titles_date,
            ).database_entry.data_timestamp
            for new_titles_date in dates
        )

    def _process_new_titles_files(
        self,
        source: Source,
        dates: list[date],
    ) -> None:
        _cache = source.shows

        for new_titles_date in dates:
            file = self._new_titles_file(source.key, new_titles_date)
            source = Source.get_one(self.db, self.plugin, file.source_key)
            timestamp = file.database_entry.data_timestamp
            _cache_sources = self._preload_sources(
                file.source_key,
                preload_seasons=True,
            ).all()

            logger.info("Processing new titles file: {}", file.database_entry.key)
            for edge in file.parsed_edges():
                full_path = edge.node.content.full_path
                match edge.node.field__typename:
                    case "Season":
                        show_key, season_key = full_path.rsplit("/", 1)
                    case "Movie":
                        show_key = full_path
                        season_key = full_path
                    case _:
                        msg = f"Unknown field__typename: {edge.node.field__typename}"
                        raise ValueError(msg)

                # Need to match on show because if this is a new season looking up an
                # existing season would fail.
                if show := Show.get_from_memory(self.db, source, show_key):
                    logger.info("Matched show: {}", show.name or show_key)
                    _cache_seasons = show.seasons
                    # If the season was found only the season needs to be updated.
                    if season := Season.get_from_memory(self.db, show, season_key):
                        season.set_update_at(timestamp)
                    # If no season was found this contains a new episode so the show
                    # needs to be updated.
                    else:
                        show.set_update_at(timestamp)

    # endregion

    # region Regex

    @classmethod
    def _url_regex(cls) -> str:
        # Example URLs:
        # https://www.justwatch.com/us/tv-show/kaiju-no-8
        # https://www.justwatch.com/us/tv-show/kaiju-no-8/season-1
        # https://www.justwatch.com/us/movie/weapons-2026
        # E501 - Splitting the regex into multiple lines does not make it more readable.
        url_string = r"(?P<show_key>\/(?P<locale>[a-zA-Z]{2})\/(?:tv-show|movie)\/.+?)(?:\/|$)(?:(?P<season_key>.+?)(?:\/|$))?"
        source_name_regex = r"^(?P<source_name>.*?)"
        domain_regex = cls._domain_regex()
        # Remove the start of string character to support choosing a source by placing
        # it in front of the URL.
        domain_regex = domain_regex.replace("^", "", 1)

        return source_name_regex + domain_regex + url_string

    # endregion

    # region Class Methods

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["justwatch.com"]

    # endregion
