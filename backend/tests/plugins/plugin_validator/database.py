# TODO: Validate
import json
from collections.abc import Generator
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from freezegun import freeze_time
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
from plugins.utils.abstract_plugin import (
    PluginSearchResults,
    URLImportResult,
)
from plugins.utils.base_plugin import BasePlugin
from tests.conftest import (
    init_db,
    savepoint_session,
    test_engine,
)
from tests.plugins.plugin_validator.serialization import SerializationMixin


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
        """Path to the directory where all files for the test class are stored."""
        return TEST_FILES_FOLDER / self.plugin_class.plugin_key() / type(self).__name__

    def stats_directory_path(self, label: str) -> Path:
        """Path to the directory where stats for a specific test are stored."""
        return self.files_directory_path() / "stats" / label

    def verification_file_path(self) -> Path:
        """Path to the file that has the expected output for the test class."""
        return self.files_directory_path() / "verification.json"

    def import_result_file_path(self) -> Path:
        """Path to the file with the expected import_url result for the test class."""
        return self.files_directory_path() / "import_result.json"

    def combined_files_path(self) -> Path:
        """Path to the combined file containing all exported database files."""
        return self.files_directory_path() / "all_files.json"

    def select_plugin_with_children(self, session: Session) -> Plugin:
        """Return a plugin with all children selectinloaded."""
        select_statement = (
            select(Plugin)
            .where(Plugin.key == self.plugin_class.plugin_key())
            .options(
                selectinload(Plugin.sources)  # type: ignore[arg-type]
                .selectinload(Source.shows)  # type: ignore[arg-type]
                .selectinload(Show.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes),  # type: ignore[arg-type]
            )
        )
        return session.exec(select_statement).one()

    def _export_all_files(self, session: Session) -> None:
        """Export all files from the database and the verification file for to disk."""
        self._export_database_files(session)
        self._export_verification_file(session)

    def _export_verification_file(self, session: Session) -> None:
        """Export the verification file to disk if it does not already exist."""
        if self.verification_file_path().exists():
            return
        plugin = self.select_plugin_with_children(session)
        plugin_dict = self._dump_model(plugin)
        self.verification_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.verification_file_path().write_text(
            json.dumps(plugin_dict, default=str, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _simplify_import_result(
        results: list[URLImportResult],
    ) -> list[dict[str, Any]]:
        """Reduce import results to the key tree that identifies their structure."""
        return [
            {
                "plugin_key": result.show.source.plugin.key,
                "source_key": result.show.source.key,
                "show_key": result.show.key,
                "seasons": [
                    {
                        "key": season.key,
                        "episodes": sorted(episode.key for episode in season.episodes),
                    }
                    for season in sorted(
                        result.show.seasons,
                        key=lambda season: season.key,
                    )
                ],
                "is_whitelist": result.is_whitelist,
                "whitelist_season_keys": sorted(
                    season.key for season in result.seasons
                ),
                "whitelist_episode_keys": sorted(
                    episode.key for episode in result.episodes
                ),
            }
            for result in results
        ]

    def _export_import_result_file(self, results: list[URLImportResult]) -> None:
        """Export the expected import result to disk if it does not already exist."""
        if self.import_result_file_path().exists():
            return
        self.import_result_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.import_result_file_path().write_text(
            json.dumps(self._simplify_import_result(results), indent=2),
            encoding="utf-8",
        )

    def _export_database_files(self, session: Session) -> None:
        """Export all files from the database to disk."""
        plugin = self.select_plugin_with_children(session)
        all_file_dicts: list[dict[str, Any]] = []
        for file in plugin.files:
            file_dict = file.model_dump()
            all_file_dicts.append(file_dict)
            self._export_database_file(file)

        combined_path = self.combined_files_path()
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        combined_path.write_text(
            json.dumps(all_file_dicts, default=str),
            encoding="utf-8",
        )

    def _export_database_file(self, file: File) -> None:
        """Export a single file from the database to disk."""
        # Make the file names NTFS compatible.
        file_id = file.key.replace(":", " - ")

        # Export the full file (metadata + content) as JSON for importing.
        metadata_path = self.files_directory_path() / f"{file_id}.metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(file.model_dump(), default=str, indent=2),
            encoding="utf-8",
        )

        # Also export the raw content file for easy inspection.
        content_path = self.files_directory_path() / file_id
        content_path.parent.mkdir(parents=True, exist_ok=True)
        file_content = file.content
        if content_path.suffix == ".json":
            with suppress(json.JSONDecodeError):
                file_content = json.dumps(json.loads(file_content or ""), indent=2)
        content_path.write_text(file_content or "", encoding="utf-8")

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

        session.commit()  # Set the rollback point.

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
        """Import all exported files into the database."""
        # Do not initialize the source until after the files are imported because
        # initializing the source often requires downloading files.
        # TODO: Can they be rewritten so this is no longer a problem?
        initialize_source = self.plugin_class.initialize_source
        self.plugin_class.initialize_source = BasePlugin.initialize_source  # type: ignore[assignment]
        plugin = self.plugin_class(session)

        plugin_user = get_or_create_plugin_user(session=session)
        plugin_db_record = Plugin.get_one(
            session,
            plugin_user,
            self.plugin_class.plugin_key(),
        )

        if self.combined_files_path().exists():
            combined_content = self.combined_files_path().read_text(encoding="utf-8")
            all_files: list[dict[str, Any]] = json.loads(combined_content)
        else:
            all_files = []
            for file_path in self.files_directory_path().rglob("*.metadata.json"):
                file_content = file_path.read_text(encoding="utf-8")
                all_files.append(json.loads(file_content))

        existing_keys = {file.key for file in plugin_db_record.files}
        for file_data in all_files:
            if file_data["key"] not in existing_keys:
                plugin_db_record.files.append(File(**file_data))

        # Files imported from JSON have raw Python types. Expiring forces SQLAlchemy to
        # re-read from the DB with proper type coercion. This is required to validate
        # datetime values.
        session.expire_all()

        # Files are imported so now initialize_source can be run.
        self.plugin_class.initialize_source = initialize_source  # type: ignore[assignment]
        plugin.initialize_source()

        session.commit()  # Set the rollback point.

    @pytest.fixture(scope="class")
    def _connection_with_files(self) -> Generator[Connection]:
        """One class-scoped connection with files imported once for the whole class.

        Both session_with_files and session_with_url share this single connection.
        Using one connection (rather than one per session fixture) is what avoids
        the deadlock: two separate open transactions inserting the same File rows
        for the same plugin would block on each other's uncommitted unique keys.
        The files are imported once here and reused by every test in the class via
        per-test savepoints.
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
        """Per-test session with files pre-imported, rolls back after each test."""
        yield from savepoint_session(_connection_with_files, nested=True)

    @pytest.fixture(scope="class")
    def _connection_with_imported_url(
        self,
        _connection_with_files: Connection,
    ) -> Generator[Connection]:
        """Import the URL once per class inside a savepoint kept open for the class.

        The savepoint is nested inside the shared files transaction, so
        session_with_files tests never see the imported URL, and it is rolled back
        when the class finishes. Both the files and the URL are therefore imported
        only once per class; per-test isolation is a further nested savepoint.
        """
        if self.invalid_url:
            pytest.skip("invalid_url is set")

        transaction = _connection_with_files.begin_nested()
        try:
            with Session(
                bind=_connection_with_files,
                join_transaction_mode="create_savepoint",
            ) as session:
                # Files are already imported on the shared connection; any download
                # here is a missing fixture, which pytest-socket fails fast.
                if self.url:
                    self._import_url(session)
                if self.search_query:
                    self._search(session, self.search_query)
            yield _connection_with_files
        finally:
            transaction.rollback()

    @pytest.fixture
    def session_with_url(
        self,
        _connection_with_imported_url: Connection,
    ) -> Generator[Session]:
        """Per-test session with files and URL imported, rolls back after each test."""
        yield from savepoint_session(_connection_with_imported_url, nested=True)
