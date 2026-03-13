# TODO: Validate
import json
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
import yaml
from sqlalchemy import Connection
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.constants import TEST_FILES_FOLDER
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.abstract_plugin import URLImportResult
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
from tests.plugins.plugin_validator.mocks import disable_ip_validation
from tests.plugins.plugin_validator.serialization import SerializationMixin


class DatabaseMixin(SerializationMixin):
    plugin_class: type[BasePlugin]
    url: str
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
        return self.files_directory_path() / "verification.yaml"

    def combined_files_path(self) -> Path:
        """Path to the combined file containing all exported database files."""
        return self.files_directory_path() / "all_files.json"

    # endregion File paths

    # region Select

    def select_plugin_with_children(self, db: Session) -> Plugin:
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
        return db.exec(select_statement).one()

    # endregion Select

    # region Export

    def _export_all_files(self, db: Session) -> None:
        """Export all files from the database and the verification file for to disk."""
        self._export_database_files(db)
        self._export_verification_file(db)

    def _export_verification_file(self, db: Session) -> None:
        """Export the verification file to disk if it does not already exist."""
        if self.verification_file_path().exists():
            return
        plugin = self.select_plugin_with_children(db)
        plugin_dict = self._dump_model(plugin)
        plugin_yaml = yaml.dump(plugin_dict, width=float("inf"))
        self.verification_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.verification_file_path().write_text(plugin_yaml, encoding="utf-8")

    def _export_database_files(self, db: Session) -> None:
        """Export all files from the database to disk."""
        plugin = self.select_plugin_with_children(db)
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

        # Export the full file (metadata + content) as YAML for importing.
        yaml_path = self.files_directory_path() / f"{file_id}.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        yaml_path.write_text(
            yaml.dump(file.model_dump(), width=float("inf")),
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
        db: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import the URL using the plugin. Files are pre-imported by the class fixture."""
        self._import_files(db)
        url = url or self.url
        with disable_ip_validation():
            plugin_instance = self.plugin_class(db, url=url)
            output = plugin_instance.import_url(url)

        db.commit()  # Set the rollback point.

        return output

    def _import_files(self, db: Session) -> None:
        """Import all exported files into the database."""
        # Initialize class to make sure plugin exists before trying to import files.
        self.plugin_class(db, url=self.url)

        plugin_user = get_or_create_plugin_user(session=db)
        plugin_db_entry = Plugin.get_one(
            db,
            self.plugin_class.plugin_key(),
            plugin_user,
        )

        if self.combined_files_path().exists():
            combined_content = self.combined_files_path().read_text(encoding="utf-8")
            all_files: list[dict[str, Any]] = json.loads(combined_content)
        else:
            # S506 - It is safe and required to import using FullLoader. It is safe
            # because all of the data is written by the test suite, and it is required
            # because that is the only way for the timestamps to be loaded correctly.
            all_files = []
            for file_path in self.files_directory_path().rglob("*.yaml"):
                if file_path.name == "verification.yaml":
                    continue
                file_content = file_path.read_text(encoding="utf-8")
                all_files.append(yaml.load(file_content, Loader=yaml.Loader))  # noqa: S506

        existing_keys = {file.key for file in plugin_db_entry.files}
        for file_data in all_files:
            if file_data["key"] not in existing_keys:
                plugin_db_entry.files.append(File(**file_data))

        db.commit()  # Set the rollback point.

    # endregion Import

    # region Fixtures

    @pytest.fixture(scope="class")
    def _db_with_files_connection(self) -> Generator[Connection]:
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

    @pytest.fixture(autouse=True)
    def db_with_files(
        self,
        _db_with_files_connection: Connection,
    ) -> Generator[Session]:
        """Per-test session with files pre-imported, rolls back after each test."""
        yield from savepoint_session(_db_with_files_connection)

    @pytest.fixture(scope="class")
    def _db_with_url_connection(self) -> Generator[Connection]:
        """Class-scoped connection with files and URL pre-imported on its own database."""
        if self.invalid_url:
            pytest.skip("invalid_url is set")
        engine = create_test_engine("url")
        reset_tables(engine)
        connection = engine.connect()
        with Session(bind=connection) as session:
            init_db(session)
            self._import_url(session)
        yield connection
        connection.close()
        engine.dispose()

    @pytest.fixture
    def db_with_url(self, _db_with_url_connection: Connection) -> Generator[Session]:
        """Per-test session with files and URL imported, rolls back after."""
        yield from savepoint_session(_db_with_url_connection)

    # endregion Fixtures
