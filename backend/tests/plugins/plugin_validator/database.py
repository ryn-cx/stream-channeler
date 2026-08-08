# TODO: Validate
import json
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from freezegun import freeze_time
from loguru import logger
from sqlalchemy import Connection
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.constants import TEST_FILES_FOLDER
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    PluginSearchResults,
    URLImportResult,
)
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.manage_plugins import import_plugins, plugins
from tests.conftest import (
    init_db,
    savepoint_session,
    test_engine,
)
from tests.plugins.plugin_validator.context_managers import stored_path
from tests.plugins.plugin_validator.serialization import SerializationMixin


def _plugin_class(plugin_key: str) -> type[BasePlugin]:
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


class DatabaseMixin[PluginT: BasePlugin](SerializationMixin):
    plugin_class: type[PluginT]
    urls: tuple[str, ...] = ()
    search_query: str | None = None
    invalid_url: bool
    imported_plugin: PluginT

    def _url_variants(self) -> list[str]:
        class_attrs = {
            key: value
            for key, value in vars(type(self)).items()
            if isinstance(value, str)
        }
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

    @property
    def url(self) -> str | None:
        variants = self._url_variants()
        return variants[0] if variants else None

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

    def stats_directory_path(self, label: str) -> Path:
        """Path to the directory where a specific test's profiling output is stored."""
        return self.files_directory_path() / "stats" / label

    def stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test of the test class."""
        return self.files_directory_path() / "stats.json"

    def slow_stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test that got worse."""
        return self.files_directory_path() / "slow.json"

    def database_dump_file_path(self) -> Path:
        """Path to the file that has the expected output for the test class."""
        return self.files_directory_path() / "database_dump.json"

    def import_url_results_file_path(self) -> Path:
        """Path to the file with the expected import_url result for the test class."""
        return self.files_directory_path() / "import_url_results.json"

    def combined_files_path(self) -> Path:
        """Path to the list of the stored files this test class needs."""
        return self.files_directory_path() / "all_files.json"

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

    def select_plugin_with_children(self, session: Session) -> Plugin:
        """Return a plugin with all children selectinloaded."""
        select_statement = self._plugin_with_children_statement().where(
            Plugin.key == self.plugin_class.plugin_key(),
        )
        return session.exec(select_statement).one()

    def select_plugins_with_children(self, session: Session) -> list[Plugin]:
        """Return every plugin in the database with all children selectinloaded."""
        statement = self._plugin_with_children_statement().order_by(Plugin.key)  # type: ignore[arg-type]
        return list(session.exec(statement).all())

    @staticmethod
    def _plugin_with_children_statement() -> Any:
        return select(Plugin).options(
            selectinload(Plugin.sources)  # type: ignore[arg-type]
            .selectinload(Source.shows)  # type: ignore[arg-type]
            .selectinload(Show.seasons)  # type: ignore[arg-type]
            .selectinload(Season.episodes),  # type: ignore[arg-type]
        )

    def _export_database_dump_file(self, session: Session) -> None:
        """Export the database dump file to disk if it does not already exist.

        A scraper can create records owned by another plugin (e.g. the TMDB
        metadata fallback), so every plugin is dumped, not only the one under test.
        """
        if self.database_dump_file_path().exists():
            return
        plugin_dicts = [
            self._dump_model(plugin)
            for plugin in self.select_plugins_with_children(session)
        ]
        self.database_dump_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.database_dump_file_path().write_text(
            json.dumps(plugin_dicts, default=str, indent=2),
            encoding="utf-8",
        )

    def load_database_dump(self) -> list[dict[str, Any]]:
        """Load every plugin's dumped state from the database dump file."""
        return json.loads(self.database_dump_file_path().read_text(encoding="utf-8"))

    def load_database_dump_plugin(self) -> Plugin:
        """Load the plugin under test from the database dump file."""
        plugin_key = self.plugin_class.plugin_key()
        for plugin_dict in self.load_database_dump():
            if plugin_dict["key"] == plugin_key:
                return self._load_model(Plugin, plugin_dict)
        msg = f"No dumped plugin for key {plugin_key!r}"
        raise ValueError(msg)

    @staticmethod
    def _simplify_import_url_results(
        results: list[URLImportResult],
    ) -> list[dict[str, Any]]:
        """Reduce import results to the identifiers a channel would take on."""
        return [
            {
                "show_identifier": result.show_identifier,
                "is_whitelist": result.is_whitelist,
                "whitelist_season_identifiers": sorted(result.season_identifiers),
                "whitelist_episode_identifiers": sorted(result.episode_identifiers),
            }
            for result in results
        ]

    def _export_import_url_results_file(self, results: list[URLImportResult]) -> None:
        """Export the expected import result to disk if it does not already exist."""
        if self.import_url_results_file_path().exists():
            return
        self.import_url_results_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.import_url_results_file_path().write_text(
            json.dumps(self._simplify_import_url_results(results), indent=2),
            encoding="utf-8",
        )

    def _import_url(
        self,
        session: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import the URL using the plugin. Files are pre-imported by the class fixture."""
        url = url or self.url
        assert url, "URL must be provided for URL import tests"
        self.imported_plugin = self.plugin_class(session)
        output = self.imported_plugin.import_url(url)

        session.flush()
        session.expire_all()

        return output

    def _search(self, session: Session, query: str) -> PluginSearchResults:
        with freeze_time(self._search_files_freeze_target(session)):
            return self.plugin_class(session).search(query)

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

    def _import_files(self, session: Session) -> None:
        """Store every stored test file as a `File` of the plugin that owns it.

        The files are put in place before a test runs so nothing has to be
        downloaded during it. `serve_downloads_from_disk` is what covers a file
        that has not been stored yet, which is only ever the case while a test's
        data is being recorded.
        """
        logger.info(f"Importing files for {type(self).__name__}")

        stored = self._files_to_import()
        plugin_user = get_or_create_plugin_user(session=session)

        # Do not initialize the source until after the files are imported because
        # initializing the source often requires downloading files.
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
            plugin_class = _plugin_class(plugin_key)
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
            plugin_records[plugin_key].files.append(
                File(
                    key=file_key,
                    content=path.read_text(encoding="utf-8") or None,
                    # Only the content of a file is stored, so when it was
                    # downloaded is taken from the stored file itself. It moves
                    # only when the file is refreshed, which is what a timestamp
                    # read off the data would have done too.
                    data_timestamp=tz_datetime.fromtimestamp(path.stat().st_mtime),
                ),
            )
            existing_keys[plugin_key].add(file_key)

        # Files imported from disk have raw Python types. Expiring forces SQLAlchemy to
        # re-read from the DB with proper type coercion. This is required to validate
        # datetime values.
        session.expire_all()

        # Files are imported so now the plugin under test's source can be run.
        assert plugin_under_test is not None
        plugin_under_test.initialize_sources()

        session.commit()  # Set the rollback point.

    @pytest.fixture(scope="class")
    def _connection_with_files(self) -> Generator[Connection]:
        """One class-scoped connection with files imported once for the whole class.

        The files are imported once here and reused by every test in the class via
        per-test savepoints, so no test re-inserts the shared File rows.
        """
        connection = test_engine.connect()
        transaction = connection.begin()
        # Clean up even when setup raises, otherwise a failed import leaks a
        # broken connection back into the pool and poisons later tests.
        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as session:
                init_db(session)
                self._import_files(session)
            yield connection
        finally:
            transaction.rollback()
            connection.close()

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
        yield from savepoint_session(_connection_with_files, nested=True)
