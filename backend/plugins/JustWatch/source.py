# TODO: Validate
from __future__ import annotations

from datetime import datetime, timedelta
from typing import override

from loguru import logger
from sqlalchemy import func
from sqlmodel import col, select

from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.JustWatch.files import NewTitleBucket, NewTitles
from plugins.JustWatch.upsert import UpsertMixin
from plugins.utils.abstract_plugin import AbstractPlugin


class SourceMixin(UpsertMixin, register=False):
    @override
    def initialize_sources(self) -> None:
        if self.plugin.sources:
            return

        providers_file = self.providers_locale_file()
        providers_file.download_if_outdated()

        bucket = self.new_titles_bucket_file(providers_file.data_timestamp)
        bucket.download_if_outdated()

        self._download_new_titles_bucket_if_missing()
        self._download_new_titles()

        self._upsert_sources()
        self.plugin.data_timestamp = self.plugin_data_timestamp()
        self.plugin.set_update_at(self.plugin.data_timestamp + timedelta(days=1))

    @override
    def update_plugin(self, plugin: Plugin) -> None:

        if not (providers_locale_file := self.providers_locale_file()):
            msg = f"Plugin {plugin.key} has no providers locale file."
            raise ValueError(msg)

        timestamp = providers_locale_file.data_timestamp + timedelta(days=1)
        providers_locale_file.download_if_outdated(timestamp)
        self._upsert_sources()
        _cache = plugin.sources
        logger.info("Updating {} JustWatch sources", len(plugin.sources))

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
        buckets = self.get_incomplete_files(
            NewTitleBucket,
            self.new_titles_bucket_file,
        )
        logger.info("Processing {} JustWatch new titles buckets", len(buckets))
        for bucket_number, bucket in enumerate(buckets, start=1):
            edges = bucket.parsed_edges()
            logger.info(
                "Processing JustWatch bucket {}/{} ({}) with {} entries",
                bucket_number,
                len(buckets),
                bucket.database_record.key,
                len(edges),
            )
            for edge_number, edge in enumerate(edges, start=1):
                short_name = edge.key.package.short_name
                source = Source.get_from_memory(self.session, self.plugin, short_name)

                # A provider without a source has no media JustWatch owns, so there
                # is nothing that its new titles could update.
                if not source:
                    continue

                logger.info(
                    "Bucket entry {}/{}: {} new titles for {}",
                    edge_number,
                    len(edges),
                    edge.key.date,
                    source.key,
                )
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

    def _title_is_tracked(self, show_key: str) -> bool:
        """Report whether the title's details are stored.

        A feed covers every title the service added, so this keeps the work to
        the handful of titles that were actually imported.
        """
        statement = select(File).where(
            File.plugin_id == self.plugin.id,
            File.key == self.url_title_details_file(show_key).file_key(),
        )
        return self.session.exec(statement).first() is not None

    def _update_tracked_title(
        self,
        show_key: str,
        source_key: str,
        timestamp: datetime,
    ) -> None:
        # A feed covers many titles, and `update_source` is not tied to any one
        # of them, so each title has to be announced before its id is resolved.
        self._set_current_show(show_key)

        title_is_stored = self._preload_show(show_key).first() is not None
        if title_is_stored:
            self._download_show_files_and_children(show_key, timestamp)

        if plugin_class := self._plugin_for_source(show_key, source_key):
            self._mark_external_show(show_key, plugin_class, timestamp)
        elif title_is_stored:
            self._import_show_for_source(show_key, source_key)

    def _import_show_for_source(self, show_key: str, source_key: str) -> None:
        logger.info("Importing {} for new source: {}", show_key, source_key)
        _cache = self._preload_sources([source_key], preload_episodes=True).all()
        self._upsert_shows(show_key, [source_key])

    def _mark_external_show(
        self,
        show_key: str,
        plugin_class: type[AbstractPlugin],
        timestamp: datetime,
    ) -> None:
        """Mark the title's copy on `source_key` when another plugin owns it.

        JustWatch watches the new titles feed of every service a title it
        imported is on, including the services whose own plugin holds the media.
        Only the copy on the service the feed belongs to changed, and it is
        stored under that plugin's own key, so the TMDB id both copies were
        matched to is the only thing that ties them together.
        """
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return

        statement = (
            select(Show)
            .join(Source)
            .join(Plugin)
            .where(
                Show.tmdb_id == tmdb_id,
                Plugin.key == plugin_class.plugin_key(),
                col(Show.deleted_at).is_(None),
            )
        )
        for external_show in self.session.exec(statement).all():
            logger.info("Marking {} show: {}", plugin_class.plugin_key(), show_key)
            external_show.set_update_at(timestamp)
            # Updating a show does not always update its seasons, so the seasons
            # have to be marked as well for the new episodes to be picked up.
            for season in external_show.active_children:
                season.set_update_at(timestamp)

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
                # The source holds no media of its own when the service has a
                # plugin, so the title changed on that plugin's copy instead.
                elif self._title_is_tracked(show_key):
                    self._update_tracked_title(
                        show_key,
                        file.source_key,
                        file.data_timestamp,
                    )
