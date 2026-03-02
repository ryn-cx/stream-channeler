# TODO: Validate
# This file is a mess, it started as couple of helper functions and grew into something
# messy that needs a major rework.
import functools
import inspect
import json
import time
import traceback
import tracemalloc
import uuid
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager, suppress
from datetime import timedelta
from pathlib import Path
from typing import Any, Concatenate, Literal, ParamSpec, TypeVar

import pyinstrument
import pytest
import yaml
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import event
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select

from app.constants import TEST_FILES_FOLDER
from app.media.models import Episode, File, Plugin, Season, Show, Source
from app.plugins.utils.abstract_plugin import URLImportResult
from app.plugins.utils.base_plugin import BasePlugin
from app.utils import tz_datetime
from tests.conftest import test_engine
from tests.plugins.validator import Validator

MockDownloadType = Callable[[], AbstractContextManager[None]]

ValidatorRuleType = Literal["Ignore", "Incremented", "Changed"]
ValidatorKey = type[BaseModel] | uuid.UUID | str

models_with_parents = list[Source | Show | Season | Episode]


class Counter:
    def __init__(self) -> None:
        self.value: int = 0


S = TypeVar("S")
P = ParamSpec("P")
R = TypeVar("R")


def skip_if(
    *attr_names: str,
) -> Callable[[Callable[Concatenate[S, P], R]], Callable[Concatenate[S, P], R]]:
    """Decorator to skip a test if any of the specified class attributes are True."""

    def decorator(
        func: Callable[Concatenate[S, P], R],
    ) -> Callable[Concatenate[S, P], R]:
        @functools.wraps(func)
        def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
            for attr_name in attr_names:
                if getattr(self, attr_name, False):
                    pytest.skip(f"Skipped because {attr_name} is True.")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def log_sql_statement_count(
    plugin_validator: PluginValidator,
    label: str,
    sql_count: Counter,
) -> Generator[None]:
    """Log the number of SQL statements executed within the context."""

    def count_statements(*_args: object, **_kwargs: object) -> None:
        sql_count.value += 1

        stack: list[traceback.FrameSummary] = traceback.extract_stack()
        callers: list[str] = [
            f"{frame.filename}:{frame.lineno} in {frame.name}"
            for frame in stack
            if ".venv" not in frame.filename
        ]
        callers_str: str = "\n  ".join(callers)

        logger.info(f"SQL #{sql_count.value}\n")
        logger.trace(f"Stack trace:\n {callers_str}")

    event.listen(test_engine, "before_cursor_execute", count_statements)
    try:
        yield
    finally:
        event.remove(test_engine, "before_cursor_execute", count_statements)
        suffix = f" [{label}]" if label else ""
        logger.info(f"SQL statements executed: {sql_count.value}{suffix}")

        stats_directory_path = plugin_validator.files_directory_path() / "stats"
        stats_directory_path.mkdir(parents=True, exist_ok=True)
        stats_file_path = stats_directory_path / label / "sql_statements.txt"
        stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        stats_file_path.write_text(str(sql_count.value))


@contextmanager
def log_execution_time(
    plugin_validator: PluginValidator,
    label: str,
) -> Generator[None]:
    """Log the execution time and memory usage within the context."""
    tracemalloc.start()
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed_time = time.perf_counter() - start_time
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        suffix = f" [{label}]" if label else ""
        logger.info(f"Execution time: {elapsed_time:.4f}s{suffix}")
        logger.info(
            f"Memory: current={current_memory / 1024 / 1024:.2f}MB, "
            f"peak={peak_memory / 1024 / 1024:.2f}MB{suffix}",
        )

        stats_directory_path = plugin_validator.files_directory_path() / "stats"
        stats_directory_path.mkdir(parents=True, exist_ok=True)
        stats_label_path = stats_directory_path / label
        stats_label_path.mkdir(parents=True, exist_ok=True)
        (stats_label_path / "execution_time.txt").write_text(str(elapsed_time))
        (stats_label_path / "peak_memory_bytes.txt").write_text(str(peak_memory))


@contextmanager
def log_flamegraph(
    plugin_validator: PluginValidator,
    label: str,
) -> Generator[None]:
    """Generate an HTML flamegraph for the code executed within the context."""
    profiler = pyinstrument.Profiler()
    profiler.start()
    try:
        yield
    finally:
        profiler.stop()

        stats_directory_path = plugin_validator.files_directory_path() / "stats"
        stats_directory_path.mkdir(parents=True, exist_ok=True)
        stats_file_path = stats_directory_path / label / "flamegraph.html"
        stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        stats_file_path.write_text(profiler.output_html())


@contextmanager
def log_stats(
    plugin_validator: PluginValidator,
    sql_count: Counter,
) -> Generator[None]:
    """Combined context manager for all stats logging."""
    label = next(
        fi.function.removeprefix("test_")
        for fi in inspect.stack()
        if fi.function.startswith("test_")
    )
    with (
        log_sql_statement_count(plugin_validator, label, sql_count),
        log_execution_time(plugin_validator, label),
        log_flamegraph(plugin_validator, label),
    ):
        yield


class PluginValidatorBase:
    # region Configuration

    plugin_class: type[BasePlugin]
    url: str
    skip_test_create_verification_files = False
    skip_test_import_url = False
    skip_test_import_existing_url = False
    skip_update_tests = False
    skip_test_update_source = False
    skip_test_update_show = False
    skip_test_update_season = False
    skip_test_update_episode = False

    # endregion

    # region File paths

    def files_directory_path(self) -> Path:
        """Path to the directory where all files for the test class are stored."""
        return (
            TEST_FILES_FOLDER / self.plugin_class.plugin_id() / self.__class__.__name__
        )

    def verification_file_path(self) -> Path:
        """Path to the file that has the expected output for the test class."""
        return self.files_directory_path() / "verification.yaml"

    # endregion

    # region Dumping
    @classmethod
    def __dump_season(cls, season: Season) -> dict[str, Any]:
        return {
            **season.model_dump(),
            "episodes": sorted(
                [episode.model_dump() for episode in season.episodes],
                key=lambda x: x["id"],
            ),
        }

    @classmethod
    def __dump_show(cls, show: Show) -> dict[str, Any]:
        return {
            **show.model_dump(),
            "seasons": sorted(
                [cls.__dump_season(season) for season in show.seasons],
                key=lambda x: x["id"],
            ),
        }

    @classmethod
    def __dump_source(cls, source: Source) -> dict[str, Any]:
        return {
            **source.model_dump(),
            "shows": sorted(
                [cls.__dump_show(show) for show in source.shows],
                key=lambda x: x["id"],
            ),
        }

    @classmethod
    def _dump_plugin(cls, plugin: Plugin) -> dict[str, Any]:
        """Recursively dump a plugin into a dict."""
        return {
            **plugin.model_dump(),
            "sources": [cls.__dump_source(source) for source in plugin.sources],
        }

    # endregion

    # region Loading

    @classmethod
    def __load_season(cls, season_data: dict[str, Any]) -> Season:
        season = Season.model_validate(season_data)
        season.episodes = [
            Episode.model_validate(episode) for episode in season_data["episodes"]
        ]
        return season

    @classmethod
    def __load_show(cls, show_data: dict[str, Any]) -> Show:
        show = Show.model_validate(show_data)
        show.seasons = [cls.__load_season(show) for show in show_data["seasons"]]
        return show

    @classmethod
    def __load_source(cls, source_data: dict[str, Any]) -> Source:
        source = Source.model_validate(source_data)
        source.shows = [cls.__load_show(season) for season in source_data["shows"]]
        return source

    @classmethod
    def _load_plugin(cls, data: dict[str, Any]) -> Plugin:
        """Recursively load a dict into a plugin."""
        plugin = Plugin.model_validate(data)
        plugin.sources = [cls.__load_source(source) for source in data["sources"]]
        return plugin

    # endregion

    # region Select

    def select_episode_with_parents(self, db: Session, episode: Episode) -> Episode:
        """Return an episode with all parents joinedloaded."""
        select_statement = (
            select(Episode)
            .where(Episode.season_id == episode.season_id, Episode.id == episode.id)
            .options(
                joinedload(Episode.season)
                .joinedload(Season.show)
                .joinedload(Show.source)
                .joinedload(Source.plugin),
            )
        )
        return db.exec(select_statement).one()

    def select_season_with_parents(self, db: Session, season: Season) -> Season:
        """Return a season with all parents joinedloaded."""
        select_statement = (
            select(Season)
            .where(Season.show_id == season.show_id, Season.id == season.id)
            .options(
                joinedload(Season.show)
                .joinedload(Show.source)
                .joinedload(Source.plugin),
            )
        )
        return db.exec(select_statement).one()

    def select_show_with_parents(self, db: Session, show: Show) -> Show:
        """Return a show with all parents joinedloaded."""
        select_statement = (
            select(Show)
            .where(Show.source_id == show.source_id, Show.id == show.id)
            .options(joinedload(Show.source).joinedload(Source.plugin))
        )
        return db.exec(select_statement).unique().one()

    def select_source_with_parents(self, db: Session, source: Source) -> Source:
        """Return a source with all parents joinedloaded."""
        select_statement = (
            select(Source)
            .where(Source.plugin_id == source.plugin_id, Source.id == source.id)
            .options(
                joinedload(Source.plugin),
            )
        )
        return db.exec(select_statement).one()

    def select_plugin_with_children(self, db: Session) -> Plugin:
        """Return a plugin with all parents joinedloaded."""
        select_statement = (
            select(Plugin)
            .where(Plugin.key == self.plugin_class.plugin_id())
            .options(
                selectinload(Plugin.sources)
                .selectinload(Source.shows)
                .selectinload(Show.seasons)
                .selectinload(Season.episodes),
            )
        )
        return db.exec(select_statement).one()

    # endregion

    # region Export

    def _export_all_files(self, db: Session) -> None:
        """Export all files from the database and the verification file for to disk."""
        self._export_database_files(db)
        self.__export_verification_file(db)

    def __export_verification_file(self, db: Session) -> None:
        """Export the verification file to disk."""
        plugin = self.select_plugin_with_children(db)
        plugin_dict = self._dump_plugin(plugin)
        plugin_yaml = yaml.dump(plugin_dict, width=float("inf"))
        self.verification_file_path().parent.mkdir(parents=True, exist_ok=True)
        self.verification_file_path().write_text(plugin_yaml, encoding="utf-8")

    def _export_database_files(self, db: Session) -> None:
        """Export all files from the database to disk."""
        plugin = self.select_plugin_with_children(db)
        for file in plugin.files:
            self.__export_database_file(file)

    def __export_database_file(self, file: File) -> None:
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
        if file.content:
            content_path = self.files_directory_path() / file_id
            content_path.parent.mkdir(parents=True, exist_ok=True)
            file_content = file.content
            if content_path.suffix == ".json":
                with suppress(json.JSONDecodeError):
                    file_content = json.dumps(json.loads(file_content), indent=2)
            content_path.write_text(file_content, encoding="utf-8")

    # endregion

    # region Import

    def _import_files_and_url(
        self,
        db: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import test files, import the URL using the plugin, and dump if needed."""
        url = url or self.url
        self._import_files(db)
        plugin_instance = self.plugin_class(db, url=url)
        output = plugin_instance.import_url(url)
        db.commit()
        return output

    def _import_files(self, db: Session) -> None:
        """Import all exported files into the database."""
        # Initialize class to make sure plugin exists before trying to import files.
        self.plugin_class(db, url=self.url)

        # Load the plugin with files joinedloaded so there are no lazy loads when adding
        # the files.
        plugin_db_entry = Plugin.get_one(
            db,
            self.plugin_class.plugin_id(),
        )

        for file_path in self.files_directory_path().rglob("*.yaml"):
            if file_path.name == "verification.yaml":
                continue
            self.__import_file(plugin_db_entry, file_path)

        db.commit()

    def __import_file(self, plugin: Plugin, file_path: Path) -> None:
        """Import a single exported file into the database."""
        # S506 - It is safe and required to import using FullLoader. It is safe because
        # all of the data is written by the test suite, and it is required because that
        # is the only way for the timestamps to be loaded correctly.
        file_content = file_path.read_text(encoding="utf-8")
        file_parsed = yaml.load(file_content, Loader=yaml.Loader)  # noqa: S506
        plugin.files.append(File(**file_parsed))

    # endregion

    # region Other

    def _get_detached_plugin(self, db: Session) -> Plugin:
        """Return a detached copy of the plugin to use for validation."""
        plugin = self.select_plugin_with_children(db)
        dumped = self._dump_plugin(plugin)
        return self._load_plugin(dumped)

    # endregion


@pytest.mark.usefixtures("disable_ip_validation")
class PluginValidator(PluginValidatorBase):
    # region Query Counts

    IMPORT_URL_QUERY_COUNT = 0
    EXISTING_URL_QUERY_COUNT = 0
    UPDATE_SOURCE_QUERY_COUNT = 0
    UPDATE_SHOW_QUERY_COUNT = 0
    UPDATE_SEASON_QUERY_COUNT = 0
    UPDATE_EPISODE_QUERY_COUNT = 0

    # endregion

    # region Validation

    def _validate_plugin(
        self,
        db: Session,
        original_plugin: Plugin,
        config: Validator,
    ) -> None:
        """Validate that the current database state matches the original plugin."""
        config.validate(original_plugin, self._get_detached_plugin(db))

    # endregion

    # region Validators

    def _import_url_validator(self) -> Validator:
        return (
            Validator()
            # These will always change because they are based on when the import occurs.
            .incremented_all("created_at", "modified_at")
            .incremented(Plugin, "data_timestamp")
            # These will all change because ids are randomly generated
            .changed_all("id")
            .changed(Source, "plugin_id")
            .changed(File, "plugin_id")
            .changed(Show, "source_id")
            .changed(Season, "show_id")
            .changed(Episode, "season_id")
        )

    def _existing_url_validator(self) -> Validator:
        return Validator()

    def _update_source_validator(self, source: Source) -> Validator:
        return (
            Validator()
            .incremented(source.id, "modified_at")
            .incremented(source.id, "data_timestamp")
        )

    def _update_show_validator(self, show: Show) -> Validator:
        return (
            Validator()
            .incremented(show.id, "modified_at")
            .incremented(show.id, "data_timestamp")
        )

    def _update_season_validator(self, season: Season) -> Validator:
        return (
            Validator()
            .incremented(season.id, "modified_at")
            .incremented(season.id, "data_timestamp")
        )

    def _update_episode_validator(self, episode: Episode) -> Validator:
        return (
            Validator()
            .incremented(episode.id, "modified_at")
            .incremented(episode.id, "data_timestamp")
        )

    # endregion

    # region Tests

    @skip_if("skip_test_create_verification_files")
    def test_initialize_test_data(
        self,
        db: Session,
        disable_ip_validation: None,
    ) -> None:
        """Downloads and exports all of the data required for the tests."""
        try:
            self._import_files_and_url(db)
            self._export_all_files(db)
        # If importing fails the downloaded files can still be dumped for analysis, but
        # the verification file should not be dumped because it is not valid.
        except Exception:
            self._export_database_files(db)
            raise

    @skip_if("skip_test_import_url")
    def test_import_url(self, db: Session, mock_download: None) -> None:
        """Import the URL and validate the data."""
        self._import_files(db)
        sql_count = Counter()
        with log_stats(self, sql_count):
            plugin_instance = self.plugin_class(db, url=self.url)
            plugin_instance.import_url(self.url)
        db.commit()

        # This is the only test that compares with the validation file because the goal
        # of this test is to make sure the imported data matches the expected data. The
        # goal of the other tests is to make sure the data updates correctly.
        verification_content = self.verification_file_path().read_text()
        # S506 - It is safe to import using fullLoader because the data was written
        # by the test suite.
        verification_data: dict[str, Any] = yaml.load(
            verification_content,
            Loader=yaml.Loader,  # noqa: S506
        )

        original_plugin = self._load_plugin(verification_data)

        self._validate_plugin(db, original_plugin, self._import_url_validator())
        assert sql_count.value <= self.IMPORT_URL_QUERY_COUNT

    @skip_if("skip_test_import_existing_url")
    def test_import_existing_url(self, db: Session, mock_download: None) -> None:
        """Test importing a URL that already exists."""
        self._import_files_and_url(db)
        original_plugin = self._get_detached_plugin(db)
        sql_count = Counter()
        with log_stats(self, sql_count):
            self.plugin_class(db, url=self.url).import_url(self.url)
        db.commit()

        self._validate_plugin(db, original_plugin, self._existing_url_validator())
        assert sql_count.value <= self.EXISTING_URL_QUERY_COUNT

    @skip_if("skip_update_tests", "skip_test_update_show")
    def test_update_show(
        self,
        db: Session,
        mock_download: MockDownloadType,
        show_index: int = 0,
    ) -> None:
        """Import the URL, update the show, and validate the data."""
        results = self._import_files_and_url(db)
        original_plugin = self._get_detached_plugin(db)
        show = results[show_index].show
        show.update_at = show.data_timestamp + timedelta(microseconds=1)
        db.commit()

        show = self.select_show_with_parents(db, show)
        sql_count = Counter()
        with log_stats(self, sql_count):
            self.plugin_class(db, show=show).update_show(show=show)
        db.commit()

        self._validate_plugin(db, original_plugin, self._update_show_validator(show))
        assert sql_count.value <= self.UPDATE_SHOW_QUERY_COUNT

    @skip_if("skip_update_tests", "skip_test_update_season")
    def test_update_season(
        self,
        db: Session,
        mock_download: MockDownloadType,
        show_index: int = 0,
        season_index: int = 0,
    ) -> None:
        """Import the URL, update the season, and validate the data."""
        results = self._import_files_and_url(db)
        original_plugin = self._get_detached_plugin(db)
        season = results[show_index].show.seasons[season_index]
        season.update_at = tz_datetime.now() + timedelta(microseconds=1)
        db.commit()

        season = self.select_season_with_parents(db, season)
        sql_count = Counter()
        with log_stats(self, sql_count):
            self.plugin_class(db, season=season).update_season(season)
        db.commit()

        self._validate_plugin(
            db,
            original_plugin,
            self._update_season_validator(season),
        )
        assert sql_count.value <= self.UPDATE_SEASON_QUERY_COUNT

    @skip_if("skip_update_tests", "skip_test_update_episode")
    def test_update_episode(
        self,
        db: Session,
        mock_download: MockDownloadType,
        show_index: int = 0,
        season_index: int = 0,
        episode_index: int = 0,
    ) -> None:
        """Import the URL, update the episode, and validate the data."""
        results = self._import_files_and_url(db)
        original_plugin = self._get_detached_plugin(db)
        episode = results[show_index].show.seasons[season_index].episodes[episode_index]
        episode.update_at = tz_datetime.now() + timedelta(microseconds=1)
        db.commit()

        episode = self.select_episode_with_parents(db, episode)
        sql_count = Counter()
        with log_stats(self, sql_count):
            self.plugin_class(db, episode=episode).update_episode(episode)
        db.commit()

        self._validate_plugin(
            db,
            original_plugin,
            self._update_episode_validator(episode),
        )
        assert sql_count.value <= self.UPDATE_EPISODE_QUERY_COUNT
