# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, override

from loguru import logger
from sqlalchemy import func
from sqlmodel import col, select

from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.JustWatch.files import NewTitleBucket, NewTitles
from plugins.JustWatch.helpers import HelperMixin


class SourceMixin(HelperMixin, register=False):
    # JustWatch tracks hundreds of providers but only the ones a title is actually
    # imported from get a `Source`, so they are created on demand instead of here.
    @override
    def initialize_source(self) -> None:
        if self.plugin.data_timestamp is None:
            providers_file = self.providers_locale_file()
            providers_file.download_if_outdated()

            bucket = self.new_titles_bucket_file(providers_file.data_timestamp)
            bucket.download_if_outdated()

            self._download_new_titles_bucket_if_missing()

            self.plugin.data_timestamp = self.plugin_data_timestamp()
            self.plugin.set_update_at(self.plugin.data_timestamp + timedelta(days=1))

    @override
    def _upsert_source(self, source_key: str) -> Source:
        """Create or update the `Source` for a single provider."""
        providers_file = self.providers_locale_file()
        providers_file.download_if_outdated()
        provider = self._provider(source_key)
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)

        source = Source(
            key=source_key,
            name=provider["clear_name"],
            favicon_url=self._favicon_url(provider),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)

        # Only use the data timestamp from the providers file for the initial
        # import. If the source already has a data_timestamp keep it because it will
        # be based on data from the new titles files which are more up to date.
        if not source.data_timestamp:
            source.data_timestamp = providers_file.data_timestamp

        return source

    def _provider(self, source_key: str) -> dict[str, Any]:
        providers = self._providers_by_key()
        if source_key not in providers:
            # A provider JustWatch added after the providers file was downloaded.
            self.providers_locale_file().download_if_outdated(tz_datetime.now())
            providers = self._providers_by_key()
        return providers[source_key]

    def _providers_by_key(self) -> dict[str, dict[str, Any]]:
        return {
            provider["short_name"]: provider
            for provider in self.providers_locale_file().parsed()
        }

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        providers_file = self.providers_locale_file()
        providers_file.download_if_outdated()

        _cache = plugin.sources
        for source in plugin.sources:
            self._upsert_source(source.key)

        self._download_latest_new_titles_bucket()
        self._process_new_titles_buckets()
        latest_bucket = self._get_latest_new_titles_bucket().one()
        plugin.data_timestamp = latest_bucket.data_timestamp
        plugin.set_update_at(latest_bucket.data_timestamp + timedelta(days=1))

    def _process_new_titles_buckets(self) -> None:
        source_key = func.split_part(col(File.key), "/", 2)
        _cache = self.session.exec(
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{NewTitles.__name__}/"),
            )
            .order_by(source_key, col(File.key).desc())
            .distinct(source_key),
        ).all()
        for bucket in self.get_incomplete_files(
            NewTitleBucket,
            self.new_titles_bucket_file,
        ):
            for edge in bucket.parsed_edges():
                short_name = edge.key.package.short_name
                source = Source.get_from_memory(self.session, self.plugin, short_name)

                # A provider without a source has no media JustWatch owns, so there
                # is nothing that its new titles could update.
                if not source:
                    continue

                new_titles_file = self.new_titles_file(source.key, edge.key.date)
                new_titles_file.download_if_outdated()
                if new_titles_file.database_record.extra != "Completed":
                    source.set_update_at(source.modified_at)

            bucket.database_record.extra = "Completed"

    @override
    def update_source(self, source: Source) -> None:
        new_titles_files = self._pending_new_titles_files(source)
        if not new_titles_files:
            msg = f"Source {source.key} has no pending new titles files to update."
            raise ValueError(msg)

        self._download_new_titles_files(new_titles_files)
        self._process_new_titles_files(source, new_titles_files)

        incomplete_minimum_timestamps: list[datetime] = []
        for new_titles_file in new_titles_files:
            minimum_timestamp = self.minimum_new_titles_timestamp(new_titles_file)

            # If the file is too new more entries may be added later, so leave it
            # unmarked (incomplete) to be reprocessed; otherwise mark it completed.
            if minimum_timestamp > new_titles_file.data_timestamp:
                incomplete_minimum_timestamps.append(minimum_timestamp)
            else:
                new_titles_file.database_record.extra = "Completed"

        source.data_timestamp = max(
            new_titles_file.data_timestamp for new_titles_file in new_titles_files
        )

        if incomplete_minimum_timestamps:
            source.set_update_at(min(incomplete_minimum_timestamps))
        else:
            source.update_at = None

    def _process_new_titles_files(
        self,
        source: Source,
        new_titles_files: list[NewTitles],
    ) -> None:
        _cache = source.shows

        for file in new_titles_files:
            source = Source.get_one(self.session, self.plugin, file.source_key)
            _cache_sources = self._preload_sources(
                file.source_key,
                preload_seasons=True,
            ).all()

            logger.info("Processing new titles file: {}", file.database_record.key)
            for edge in file.parsed_edges():
                node = edge.node
                full_path = node.content.full_path
                match node.field__typename:
                    case "Season":
                        show_key = full_path.rsplit("/", 1)[0]
                    case "Movie":
                        show_key = full_path
                    case _:
                        msg = f"Unknown field__typename: {node.field__typename}"
                        raise ValueError(msg)

                # Need to match on show because if this is a new season looking up an
                # existing season would fail.
                if show := Show.get_from_memory(self.session, source, show_key):
                    logger.info("Matched show: {}", show.name or show_key)
                    _cache_seasons = show.seasons
                    # `node.id` is JustWatch's global id for the season (or movie),
                    # which is exactly the key the season is stored under.
                    if season := Season.get_from_memory(self.session, show, node.id):
                        season.set_update_at(file.data_timestamp)
                    # If no season was found this is a new season so the show needs
                    # to be updated.
                    else:
                        show.set_update_at(file.data_timestamp)
