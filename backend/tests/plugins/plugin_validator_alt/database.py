# TODO: Validate
"""Putting the stored files in place and reading back what they built.

The store itself, and everything that serves a download out of it, is the
existing validator's: `tests.old_mess.plugins.plugin_validator.context_managers`
is imported rather than copied, so a file downloaded by either validator is the
same stored file the other one reads.
"""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from loguru import logger
from sqlalchemy import Connection
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.constants import TEST_FILES_FOLDER
from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from plugins.utils.abstract_plugin import PluginSearchResults, URLImportResult
from plugins.utils.base_plugin import BaseFile, BasePlugin
from plugins.utils.manage_plugins import import_plugins, plugins
from tests.conftest import init_db, savepoint_session, test_engine
from tests.old_mess.plugins.plugin_validator.context_managers import (
    stored_file_record,
    stored_path,
)

IMPORT_TIME = datetime(2026, 1, 1, tzinfo=UTC)
"""When every import is taken to have happened, and every file arrived."""

UPDATE_TIME = datetime(2026, 1, 2, tzinfo=UTC)
"""When every update is taken to have happened, the day after the import."""


# TODO: Validate
def date_at_import_time(record: File) -> None:
    """Date `record` as though it had been downloaded at `IMPORT_TIME`.

    A stored file is dated by when it was really downloaded, which is whenever
    the store was last topped up and never the same twice, and everything a
    plugin works out from a file is dated from the file. Reading every file as
    though it arrived at the moment the test is frozen to is what leaves the
    records built from it the same on every run.

    It is also what keeps a plugin doing what it does in production. A file left
    at the day it was really downloaded is a file the frozen clock is years past,
    so every record read out of it is due a refresh the moment it is written, and
    an import ends up walking the paths that only a stale record reaches.

    How long the file was good for is carried over as the gap it was stored with,
    so a file is still refreshed when the plugin says it should be rather than
    being made to look fresh forever. The gap survives the shift, which leaves
    dating a record that has already been dated a no-op.
    """
    refresh_gap = record.update_at - record.data_timestamp if record.update_at else None
    record.created_at = IMPORT_TIME
    record.modified_at = IMPORT_TIME
    record.data_timestamp = IMPORT_TIME
    record.update_at = IMPORT_TIME + refresh_gap if refresh_gap else None


# TODO: Validate
@contextmanager
def date_downloads_at_import_time() -> Generator[None]:
    """Date every file served during the run at `IMPORT_TIME`.

    Wrapped around whatever is already serving downloads rather than replacing
    it, so the store stays the existing validator's and only the dates a file
    arrives with are this validator's own.
    """
    served_download_if_outdated = BaseFile[Any].download_if_outdated

    # TODO: Validate
    def _download_if_outdated(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        served_download_if_outdated(self, update_at)
        record = self._existing_database_record
        if record is not None:
            date_at_import_time(record)

    with patch.object(BaseFile, "download_if_outdated", _download_if_outdated):
        yield


# TODO: Validate
def plugin_class_for(plugin_key: str) -> type[BasePlugin]:
    """Return the plugin class for a plugin key.

    Unregistered plugins are included because a registered plugin can create
    records owned by one (e.g. JustWatch creating Disney+ sources).
    """
    import_plugins()
    for plugin_class in plugins:
        if plugin_class.plugin_key() == plugin_key:
            return plugin_class  # type: ignore[return-value]

    remaining: list[type[BasePlugin]] = [BasePlugin]
    while remaining:
        plugin_class = remaining.pop()
        remaining.extend(plugin_class.__subclasses__())
        if plugin_class.plugin_key() == plugin_key:
            return plugin_class
    msg = f"No plugin found for key {plugin_key!r}"
    raise ValueError(msg)


# TODO: Validate
class DatabaseMixinAlt[PluginT: BasePlugin]:
    """Everything a test needs in place before it can dump anything."""

    plugin_class: type[PluginT]
    urls: tuple[str, ...] = ()
    search_url: str | None = None
    search_query: str | None = None
    invalid_url: bool = False
    imported_plugin: PluginT

    # TODO: Validate
    def _url_variants(self) -> list[str]:
        class_attrs: dict[str, str] = {}
        for klass in reversed(type(self).__mro__):
            class_attrs.update(
                {
                    key: value
                    for key, value in vars(klass).items()
                    if isinstance(value, str)
                },
            )
        variants: list[str] = []
        for url in self.urls:
            formatted = url.format(**class_attrs)
            if formatted.startswith("/"):
                variants += [
                    domain + formatted for domain in self.plugin_class.domains()
                ]
            else:
                variants.append(formatted)
        return variants

    # TODO: Validate
    @property
    def url(self) -> str | None:
        variants = self._url_variants()
        return variants[0] if variants else None

    # TODO: Validate
    def files_directory_path(self) -> Path:
        """Path to the directory where all files for the test class are stored.

        The test's file name is a folder of its own so two test classes that share
        a name but live in different files do not share a directory.
        """
        test_class = type(self)
        file_name = test_class.__module__.rsplit(".", maxsplit=1)[-1]
        return (
            TEST_FILES_FOLDER
            / self.plugin_class.plugin_key()
            / file_name
            / test_class.__name__
        )

    # TODO: Validate
    def combined_files_path(self) -> Path:
        """Path to the list of the stored files this test class needs."""
        return self.files_directory_path() / "all_files.json"

    # TODO: Validate
    def expected_state_path(self, label: str) -> Path:
        """Path to the dump the test `label` names recorded the first time it ran."""
        return self.files_directory_path() / "alt_state" / f"{label}.json"

    # TODO: Validate
    def incorrect_state_path(self, label: str) -> Path:
        """Path to the dump the test `label` names produced when it last failed."""
        return self.files_directory_path() / "alt_incorrect_state" / f"{label}.json"

    # TODO: Validate
    def stats_directory_path(self, label: str) -> Path:
        """Path to the directory where a specific test's profiling output is stored."""
        return self.files_directory_path() / "alt_stats" / label

    # TODO: Validate
    def stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test of the test class."""
        return self.files_directory_path() / "alt_stats.json"

    # TODO: Validate
    def slow_stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test that got worse."""
        return self.files_directory_path() / "alt_slow.json"

    # TODO: Validate
    def _export_files_manifest(self, session: Session) -> None:
        """Record which of the stored files this test class needs.

        Only the names are recorded. The files themselves are shared by every
        test that reaches for them, so all that belongs to one test is which of
        them it uses, which is what keeps a test from importing the whole store.
        """
        statement = select(File.key, Plugin.key).join(Plugin)
        entries = sorted(
            {
                (plugin_key, file_key)
                for file_key, plugin_key in session.exec(statement).all()
            },
        )
        self.combined_files_path().parent.mkdir(parents=True, exist_ok=True)
        self.combined_files_path().write_text(
            json.dumps(
                [
                    {"plugin_key": plugin_key, "key": file_key}
                    for plugin_key, file_key in entries
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    # TODO: Validate
    def _files_to_import(self) -> list[tuple[str, str, Path]]:
        """Return the plugin key, file key and stored path of each file needed.

        A file the manifest names that is not stored is left out rather than
        raised over, so recording a test's data can fill in whatever is missing.
        """
        if not self.combined_files_path().exists():
            return []
        entries = json.loads(self.combined_files_path().read_text(encoding="utf-8"))
        files = [
            (
                entry["plugin_key"],
                entry["key"],
                stored_path(entry["plugin_key"], entry["key"]),
            )
            for entry in entries
        ]
        return [
            (plugin_key, key, path) for plugin_key, key, path in files if path.is_file()
        ]

    # TODO: Validate
    @staticmethod
    def _owning_plugin_key(entity: Plugin | Source | Show | Season | Episode) -> str:
        """Return the key of the plugin whose records `entity` is one of."""
        match entity:
            case Plugin() as plugin:
                return plugin.key
            case Source() as source:
                return source.plugin.key
            case Show() as show:
                return show.source.plugin.key
            case Season() as season:
                return season.show.source.plugin.key
            case Episode() as episode:
                return episode.season.show.source.plugin.key

    # TODO: Validate
    def owning_plugin(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> BasePlugin:
        """Return the plugin that reads and writes `entity`.

        An import can store a record under another plugin - TMDB keeps a title
        as canonical media and hands the listing on to the service that streams
        it - and only the plugin a record belongs to knows how to read it. So
        what updates a record is looked up from the record rather than taken to
        be the plugin under test.

        One plugin is built per key and kept for as long as the session it reads
        through, because building one reaches the database - it looks up the user
        every plugin runs as - and a test that updates every record of a kind
        would otherwise build the same plugin once per record and pay for it
        every time.
        """
        plugin_key = self._owning_plugin_key(entity)
        if plugin_key == self.plugin_class.plugin_key():
            return self.imported_plugin
        built: dict[str, BasePlugin] = session.info.setdefault("owning_plugins", {})
        if plugin_key not in built:
            built[plugin_key] = plugin_class_for(plugin_key)(session)
        return built[plugin_key]

    # TODO: Validate
    def select_plugin_with_children(self, session: Session) -> Plugin:
        """Return the plugin under test with all children selectinloaded."""
        statement = self._plugin_with_children_statement().where(
            Plugin.key == self.plugin_class.plugin_key(),
        )
        return session.exec(statement).one()

    # TODO: Validate
    def select_plugins_with_children(self, session: Session) -> list[Plugin]:
        """Return every plugin in the database with all children selectinloaded."""
        statement = self._plugin_with_children_statement().order_by(Plugin.key)
        return list(session.exec(statement).all())

    # TODO: Validate
    @staticmethod
    def _plugin_with_children_statement() -> SelectOfScalar[Plugin]:
        return select(Plugin).options(
            selectinload(Plugin.sources)  # type: ignore[arg-type]
            .selectinload(Source.shows)  # type: ignore[arg-type]
            .selectinload(Show.seasons)  # type: ignore[arg-type]
            .selectinload(Season.episodes),  # type: ignore[arg-type]
        )

    # TODO: Validate
    @staticmethod
    def simplify_import_url_results(
        results: list[URLImportResult],
    ) -> list[dict[str, Any]]:
        """Reduce import results to the records a channel would take on."""
        return sorted(
            (
                {
                    "show_key": result.show_key,
                    "is_whitelist": result.is_whitelist,
                    "whitelist_season_keys": sorted(result.season_keys),
                    "whitelist_episode_keys": sorted(result.episode_keys),
                }
                for result in results
            ),
            key=lambda result: result["show_key"],
        )

    # TODO: Validate
    def _import_url(
        self,
        session: Session,
        url: str | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        """Import the URL using the plugin. Files are pre-imported by the class fixture."""
        url = url or self.url
        assert url, "URL must be provided for URL import tests"
        self.imported_plugin = self.plugin_class(session)
        output = self.imported_plugin.import_url(url, force=force)

        session.flush()
        session.expire_all()

        return output

    # TODO: Validate
    def _search(self, session: Session, query: str) -> PluginSearchResults:
        with freeze_time(self._search_files_freeze_target(session)):
            return self.plugin_class(session).search(query)

    # TODO: Validate
    def _search_files_freeze_target(self, session: Session) -> datetime | None:
        plugin = self.select_plugin_with_children(session)
        search_timestamps = [
            file.data_timestamp
            for file in plugin.files
            if file.key.startswith("Search")
        ]
        if not search_timestamps:
            return None
        return max(search_timestamps) + timedelta(seconds=1)

    # TODO: Validate
    def _import_files(self, session: Session) -> None:
        """Store every stored test file as a `File` of the plugin that owns it.

        The files are put in place before a test runs so nothing has to be
        downloaded during it. `serve_downloads_from_disk`, which the plugin
        conftest holds open for the whole session, is what covers a file that has
        not been stored yet, which is only ever the case while a test's data is
        being recorded.

        Held at the frozen import time because this is also where a plugin's
        sources are initialized, and a source dated by the clock the machine
        happened to be at is a record that is different on every run.
        """
        logger.info(f"Importing files for {type(self).__name__}")

        stored = self._files_to_import()
        plugin_user = get_or_create_plugin_user(session=session)

        # Do not initialize the source until after the files are imported because
        # initializing the source often requires downloading files.
        # TODO: Validate
        def no_operation(_plugin: BasePlugin) -> None:
            """No operation function."""

        # A file can belong to a different plugin than the one under test (e.g. TMDB
        # fallback files), so create a record for each owning plugin. Sources are
        # only initialized for the plugin under test, at the end.
        plugin_keys = {plugin_key for plugin_key, _key, _path in stored}
        plugin_keys.add(self.plugin_class.plugin_key())

        plugin_records: dict[str, Plugin] = {}
        plugin_under_test: BasePlugin | None = None
        for plugin_key in plugin_keys:
            plugin_class = plugin_class_for(plugin_key)
            initialize_sources = plugin_class.initialize_sources
            plugin_class.initialize_sources = no_operation  # type: ignore[assignment]
            try:
                plugin_instance = plugin_class(session)
            finally:
                plugin_class.initialize_sources = initialize_sources  # type: ignore[method-assign]
            if plugin_key == self.plugin_class.plugin_key():
                plugin_under_test = plugin_instance
            plugin_records[plugin_key] = Plugin.get_one(
                session,
                plugin_user,
                plugin_key,
            )

        existing_keys = {
            plugin_key: {file.key for file in record.files}
            for plugin_key, record in plugin_records.items()
        }
        for plugin_key, file_key, path in stored:
            if file_key in existing_keys[plugin_key]:
                continue
            record = stored_file_record(plugin_key, file_key, path)
            date_at_import_time(record)
            plugin_records[plugin_key].files.append(record)
            existing_keys[plugin_key].add(file_key)

        # Files imported from disk have raw Python types. Expiring forces SQLAlchemy to
        # re-read from the DB with proper type coercion. This is required to validate
        # datetime values.
        session.expire_all()

        # Files are imported so now the plugin under test's source can be run.
        assert plugin_under_test is not None
        plugin_under_test.initialize_sources()

        session.commit()  # Set the rollback point.

    # TODO: Validate
    @pytest.fixture(scope="class")
    def _connection_with_files(self) -> Generator[Connection]:
        """One class-scoped connection with files imported once for the whole class.

        The files are imported once here and reused by every test in the class via
        per-test savepoints, so no test re-inserts the shared `File` rows.

        One connection and no more, because a second one would sit behind this
        one's open transaction the moment it wrote a row this one had already
        written - the plugin user being the first of them - and wait on it for as
        long as the class ran.
        """
        connection = test_engine.connect()
        transaction = connection.begin()
        # Clean up even when setup raises, otherwise a failed import leaks a
        # broken connection back into the pool and poisons later tests.
        try:
            # `init_db` is held at the frozen time too, the users it writes
            # being rows the dump compares like any other.
            with (
                Session(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                ) as session,
                freeze_time(IMPORT_TIME),
                date_downloads_at_import_time(),
            ):
                init_db(session)
                self._import_files(session)
            yield connection
        finally:
            transaction.rollback()
            connection.close()

    # TODO: Validate
    @pytest.fixture
    def session_with_files(
        self,
        _connection_with_files: Connection,
    ) -> Generator[Session]:
        """Per-test session that rolls back after each test.

        Tests that need imported URL data call `_import_url` themselves at the start
        of the test; the import runs inside the per-test savepoint and rolls back with
        it, so each test owns its own initialized plugin without any shared URL fixture.
        """
        with date_downloads_at_import_time():
            yield from savepoint_session(_connection_with_files, nested=True)
