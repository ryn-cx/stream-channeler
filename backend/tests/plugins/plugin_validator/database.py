# TODO: Validate
"""Putting the stored files in place and reading back what they built."""

import json
from collections.abc import Generator, Iterable, Sequence
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from loguru import logger
from sqlalchemy import Connection
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.models import Channel
from app.constants import TEST_RESULTS_FOLDER
from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.linking import link_plugin_title_to_tmdb
from plugins.utils.abstract_plugin import AbstractPlugin, URLImportResult
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.manage_plugins import import_plugins, plugins
from tests.conftest import init_db, savepoint_session, test_engine
from tests.plugins.frozen_clock import frozen_clock
from tests.plugins.plugin_validator.stored_files import (
    IMPORT_TIME,
    UPDATE_TIME,
    date_at_import_time,
    stored_path,
)


# TODO: Validate
def match_imported_titles_to_tmdb(
    session: Session,
    plugin_instance: AbstractPlugin,
    titles: Sequence[Title],
) -> None:
    """Search TMDB for every title `plugin_instance` imported and link what is found.

    A title already linked to a title is left as it is, since the link it carries
    may have been settled by hand.
    """
    for title in titles:
        if not title.is_canonical:
            continue
        link_plugin_title_to_tmdb(
            session,
            title,
            plugin_instance.tmdb_lookup_info(title),
        )


# TODO: Validate
@contextmanager
def date_downloads_at_import_time(import_time: datetime) -> Generator[None]:
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
            date_at_import_time(record, import_time)

    with (
        patch.object(BaseFile, "download_if_outdated", _download_if_outdated),
    ):
        yield


# TODO: Validate
@contextmanager
def no_channel_initialization(
    plugin_classes: Iterable[type[AbstractPlugin]],
) -> Generator[None]:
    with ExitStack() as stack:
        for plugin_class in plugin_classes:
            stack.enter_context(
                patch.object(
                    plugin_class,
                    "_create_channel_records",
                    lambda _self: None,
                ),
            )
        yield


# TODO: Validate
@contextmanager
def only_registered_plugins(
    plugin_classes: Iterable[type[AbstractPlugin]],
) -> Generator[None]:
    """Leave only `plugin_classes` registered for as long as the block runs.

    The registry every lookup reads is one set built at import time, so the set
    itself is emptied and refilled rather than replaced: a replacement would be
    seen by whatever reads the module attribute and missed by everything that
    took the name into its own namespace.
    """
    import_plugins()
    original = set(plugins)
    plugins.clear()
    plugins.update(plugin_classes)
    try:
        yield
    finally:
        plugins.clear()
        plugins.update(original)


# TODO: Validate
def plugin_class_for(plugin_key: str) -> type[AbstractPlugin]:
    """Return the plugin class for a plugin key.

    Unregistered plugins are included because a registered plugin can create
    records owned by one (e.g. JustWatch creating Disney+ sources).
    """
    import_plugins()
    for plugin_class in plugins:
        if plugin_class.plugin_name() == plugin_key:
            return plugin_class

    remaining: list[type[AbstractPlugin]] = [AbstractPlugin]
    while remaining:
        plugin_class = remaining.pop()
        remaining.extend(plugin_class.__subclasses__())
        if plugin_class.plugin_name() == plugin_key:
            return plugin_class
    msg = f"No plugin found for key {plugin_key!r}"
    raise ValueError(msg)


# TODO: Validate
class DatabaseMixin[PluginT: AbstractPlugin]:
    """Everything a test needs in place before it can dump anything."""

    plugin_class: type[PluginT]
    urls: tuple[str, ...] = ()
    import_time: datetime = IMPORT_TIME
    update_time: datetime = UPDATE_TIME
    invalid_url: bool = False
    initializes_channels: bool = False
    initializes_tmdb: bool = False
    restrict_registered_plugins: bool = True
    imported_plugin: PluginT

    # TODO: Validate
    def __init_subclass__(cls, **kwargs: object) -> None:
        """Follow a class that moved its import with an update the day after it."""
        super().__init_subclass__(**kwargs)
        if "import_time" in cls.__dict__ and "update_time" not in cls.__dict__:
            cls.update_time = cls.import_time + timedelta(days=1)

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
                    domain + formatted
                    for domain in self.plugin_class._domains()  # type: ignore[attr-defined]  # noqa: SLF001
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
            TEST_RESULTS_FOLDER
            / self.plugin_class.plugin_name()
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
        return self.files_directory_path() / "state" / f"{label}.json"

    # TODO: Validate
    def incorrect_state_path(self, label: str) -> Path:
        """Path to the dump the test `label` names produced when it last failed."""
        return self.files_directory_path() / "incorrect_state" / f"{label}.json"

    # TODO: Validate
    def stats_directory_path(self, label: str) -> Path:
        """Path to the directory where a specific test's profiling output is stored."""
        return self.files_directory_path() / "stats" / label

    # TODO: Validate
    def stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test of the test class."""
        return self.files_directory_path() / "stats.json"

    # TODO: Validate
    def slow_stats_file_path(self) -> Path:
        """Path to the file holding the stats of every test that got worse."""
        return self.files_directory_path() / "slow.json"

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
    def _owning_plugin_key(entity: Plugin | Source | Title | Season | Episode) -> str:
        """Return the key of the plugin whose records `entity` is one of."""
        match entity:
            case Plugin() as plugin:
                return plugin.key
            case Source() as source:
                return source.plugin.key
            case Title() as title:
                return title.source.plugin.key
            case Season() as season:
                return season.title.source.plugin.key
            case Episode() as episode:
                return episode.season.title.source.plugin.key

    # TODO: Validate
    def owning_plugin(
        self,
        session: Session,
        entity: Plugin | Source | Title | Season | Episode,
    ) -> AbstractPlugin:
        """Return the plugin that reads and writes `entity`.

        An import can store a record under another plugin - TMDB keeps a title
        as canonical media and hands the listing on to the service that streams
        it - and only the plugin a record belongs to knows how to read it. So
        what updates a record is looked up from the record rather than taken to
        be the plugin under test.

        One plugin is built per key and kept for as long as the session it reads
        through.
        """
        plugin_key = self._owning_plugin_key(entity)
        if plugin_key == self.plugin_class.plugin_name():
            return self.imported_plugin
        built: dict[str, AbstractPlugin] = session.info.setdefault("owning_plugins", {})
        if plugin_key not in built:
            built[plugin_key] = plugin_class_for(plugin_key)(session)
        return built[plugin_key]

    # TODO: Validate
    def select_plugin_with_children(self, session: Session) -> Plugin:
        """Return the plugin under test with all children selectinloaded."""
        statement = self._plugin_with_children_statement().where(
            Plugin.key == self.plugin_class.plugin_name(),
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
            .selectinload(Source.titles)  # type: ignore[arg-type]
            .selectinload(Title.seasons)  # type: ignore[arg-type]
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
                    "title_key": result.title.key,
                    "is_whitelist": result.is_whitelist,
                    "whitelist_season_keys": sorted(result.season_keys),
                    "whitelist_episode_keys": sorted(result.episode_keys),
                }
                for result in results
            ),
            key=lambda result: result["title_key"],
        )

    # TODO: Validate
    @staticmethod
    def _delete_channels(session: Session) -> None:
        for channel in session.exec(select(Channel)).all():
            session.delete(channel)
        session.flush()
        session.expire_all()

    # TODO: Validate
    def _import_url(
        self,
        session: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import the URL using the plugin."""
        url = url or self.url
        assert url, "URL must be provided for URL import tests"
        self._delete_channels(session)
        self.imported_plugin = self.plugin_class(session)
        output = self.imported_plugin.validate_and_import_url(url)

        session.flush()
        session.expire_all()

        return output

    # TODO: Validate
    def _registered_plugin_classes(self) -> list[type[AbstractPlugin]]:
        """Return the plugins a run of this class is allowed to see.

        Every other plugin is left unregistered, so what a URL is looked up
        against is the plugin under test, the plugins whose stored files say
        they take part, and TMDB where the class says it reaches for it.
        """
        plugin_keys = {
            plugin_key for plugin_key, _key, _path in self._files_to_import()
        }
        if self.initializes_tmdb:
            plugin_keys.add("TMDB")
        plugin_keys.add(self.plugin_class.plugin_name())
        return [plugin_class_for(plugin_key) for plugin_key in sorted(plugin_keys)]

    # TODO: Validate
    @pytest.fixture(scope="class", autouse=True)
    def _registered_plugins(self) -> Generator[None]:
        if not self.restrict_registered_plugins:
            yield
            return
        with only_registered_plugins(self._registered_plugin_classes()):
            yield

    # TODO: Validate
    def _initialize_plugins(self, session: Session) -> None:
        logger.info(f"Initializing plugins for {type(self).__name__}")

        plugin_keys = {
            plugin_key for plugin_key, _key, _path in self._files_to_import()
        }
        if self.initializes_tmdb:
            plugin_keys.add("TMDB")
        if self.initializes_channels:
            plugin_keys.discard(self.plugin_class.plugin_name())
        else:
            plugin_keys.add(self.plugin_class.plugin_name())

        plugin_classes = [
            plugin_class_for(plugin_key) for plugin_key in sorted(plugin_keys)
        ]
        with no_channel_initialization(plugin_classes):
            for plugin_class in plugin_classes:
                plugin_class.initialize_plugin(session)

        session.expire_all()
        session.commit()  # Set the rollback point.

    # TODO: Validate
    @pytest.fixture(scope="class")
    def _connection_with_files(self) -> Generator[Connection]:
        """One class-scoped connection set up once for the whole class.

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
                frozen_clock(self.import_time),
                date_downloads_at_import_time(self.import_time),
            ):
                init_db(session)
                self._initialize_plugins(session)
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
        with date_downloads_at_import_time(self.import_time):
            yield from savepoint_session(_connection_with_files, nested=True)
