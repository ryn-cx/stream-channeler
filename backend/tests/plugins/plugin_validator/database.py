# TODO: Validate
import json
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.constants import TEST_FILES_FOLDER
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.abstract_plugin import (
    PluginSearchResults,
    URLImportResult,
)
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from tests.conftest import (
    create_test_engine,
    init_db,
    reset_tables,
    savepoint_session,
)
from tests.plugins.plugin_validator.mocks import block_downloads
from tests.plugins.plugin_validator.serialization import SerializationMixin


class DatabaseMixin[PluginT: BasePlugin](SerializationMixin):
    plugin_class: type[PluginT]
    url: str | None = None
    search_query: str | None = None
    invalid_url: bool

    # region File paths

    def files_directory_path(self) -> Path:
        """Path to the directory where all files for the test class are stored."""
        return TEST_FILES_FOLDER / self.plugin_class.plugin_key() / type(self).__name__

    def stats_directory_path(self, label: str) -> Path:
        """Path to the directory where stats for a specific test are stored."""
        return self.files_directory_path() / "stats" / label

    def verification_file_path(self) -> Path:
        """Path to the file that has the expected output for the test class."""
        return self.files_directory_path() / "verification.json"

    def combined_files_path(self) -> Path:
        """Path to the combined file containing all exported database files."""
        return self.files_directory_path() / "all_files.json"

    # endregion File paths

    # region Select

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

    # endregion Select

    # region Export

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

    # endregion Export

    # region Import

    def _import_url(
        self,
        session: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import the URL using the plugin. Files are pre-imported by the class fixture."""
        url = url or self.url
        assert url, "URL must be provided for URL import tests"
        output = self.plugin_class(session).import_url(url)

        session.commit()  # Set the rollback point.

        return output

    def _search(self, session: Session, query: str) -> PluginSearchResults:
        """Search using the plugin. Files are pre-imported by the class fixture."""
        return self.plugin_class(session).search(query)

    def _import_files(self, session: Session) -> None:
        """Import all exported files into the database."""
        # Mock initialize_database to only run the BasePlugin implementation (creates the
        # database record) without running subclass logic that would try to download
        # files before the cached test data is loaded.
        original_initialize = self.plugin_class.initialize_database
        self.plugin_class.initialize_database = BasePlugin.initialize_database  # type: ignore[assignment]
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

        # Run the full initialize_database now that the files are imported.
        self.plugin_class.initialize_database = original_initialize  # type: ignore[assignment]
        plugin.initialize_database()

        session.commit()  # Set the rollback point.

    # endregion Import

    # region Fixtures

    @pytest.fixture(scope="class")
    def _session_with_files_connection(self) -> Generator[Connection]:
        """Class-scoped connection with files pre-imported on its own database."""
        engine = create_test_engine("files")
        reset_tables(engine)
        connection = engine.connect()
        with Session(bind=connection) as session:
            init_db(session)
            self._import_files(session)
        yield connection
        connection.close()
        engine.dispose()

    @pytest.fixture
    def session_with_files(
        self,
        _session_with_files_connection: Connection,
    ) -> Generator[Session]:
        """Per-test session with files pre-imported, rolls back after each test."""
        yield from savepoint_session(_session_with_files_connection)

    @pytest.fixture(scope="class")
    def _session_with_url_connection(self) -> Generator[Connection]:
        """Class-scoped connection with files and URL pre-imported on its own database."""
        if self.invalid_url:
            pytest.skip("invalid_url is set")
        if not self.url and not self.search_query:
            pytest.skip("No URL or search query defined")

        engine = create_test_engine("url")
        reset_tables(engine)
        connection = engine.connect()
        with Session(bind=connection) as session:
            init_db(session)
            self._import_files(session)
            with block_downloads():
                if self.url:
                    self._import_url(session)
                if self.search_query:
                    self._search(session, self.search_query)
        yield connection
        connection.close()
        engine.dispose()

    @pytest.fixture
    def session_with_url(
        self,
        _session_with_url_connection: Connection,
    ) -> Generator[Session]:
        """Per-test session with files and URL imported, rolls back after."""
        yield from savepoint_session(_session_with_url_connection)

    # endregion Fixtures
