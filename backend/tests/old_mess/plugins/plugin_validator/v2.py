# TODO: Validate
import difflib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from sqlmodel import Session

from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin import BasePlugin
from tests.old_mess.plugins.plugin_validator import PluginValidator
from tests.old_mess.plugins.plugin_validator import database as database_module
from tests.old_mess.plugins.plugin_validator.canonical_links import (
    collect_canonical_links,
)
from tests.old_mess.plugins.plugin_validator.context_managers import (
    mock_update,
    stored_file_record,
)
from tests.old_mess.plugins.plugin_validator.log_stats import log_stats
from tests.old_mess.plugins.plugin_validator.serialization import CHILDREN, Record

IMPORT_TIME = datetime(2026, 1, 1, tzinfo=UTC)
"""When every import is taken to have happened."""

UPDATE_TIME = datetime(2026, 1, 2, tzinfo=UTC)
"""When every update is taken to have happened, a month after the import."""

# The id of a record is generated afresh on every run and so is the same thing
# said twice: it is never equal between two runs and never means anything when it
# is. Which record points at which is said by `canonical_links` and by the shape
# of the tree instead, both of which are written in keys.
_VOLATILE_FIELD = "id"
_VOLATILE_SUFFIX = "_id"


# TODO: Validate
def _dump_value(value: object) -> object:
    """Return `value` as something JSON holds and two runs write the same way."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value


# TODO: Validate
def _dump_record(record: Record) -> dict[str, Any]:
    """Dump a record and its children, leaving out what a run generates afresh."""
    data = {
        name: _dump_value(value)
        for name, value in record.model_dump().items()
        if name != _VOLATILE_FIELD and not name.endswith(_VOLATILE_SUFFIX)
    }
    if entry := CHILDREN.get(type(record)):
        child_name, _ = entry
        data[child_name] = sorted(
            (_dump_record(child) for child in getattr(record, child_name)),
            key=lambda child: child["key"],
        )
    return data


# TODO: Validate
def _dated_file_record(owner_key: str, file_key: str, path: Path) -> File:
    """Return the stored file as it would have been downloaded at `IMPORT_TIME`.

    A stored file is dated by when it was really downloaded, which is whenever
    the store was last topped up and never the same twice. Everything a plugin
    works out from a file is dated from the file, so a file dated by the clock
    the test is frozen to is what makes the records it produces the same on
    every run. How long the file was good for is kept as the gap it was stored
    as, so a file is still refreshed when the plugin says it should be.
    """
    record = stored_file_record(owner_key, file_key, path)
    refresh_gap = record.update_at - record.data_timestamp if record.update_at else None
    record.created_at = IMPORT_TIME
    record.modified_at = IMPORT_TIME
    record.data_timestamp = IMPORT_TIME
    record.update_at = IMPORT_TIME + refresh_gap if refresh_gap else None
    return record


# TODO: Validate
class PluginValidatorV2[PluginT: BasePlugin](PluginValidator[PluginT]):
    """A plugin test whose clock is fixed and whose check is one saved dump.

    The rules a `Validator` carries are what a test needs when it cannot say
    what a value will be, only how it should move. Fixing the clock takes that
    away: an import happens on the 1st of January and an update a month later,
    every file is dated by the import, and the only thing left that a run
    generates afresh is a record's id, which is left out of the dump. What a
    test compares is then the whole database against the dump saved the first
    time it ran, which is written and failed over so that what was recorded is
    read before it is trusted.
    """

    # TODO: Validate
    def expected_state_path(self, label: str) -> Path:
        """Path to the state `label` recorded the first time it ran."""
        return self.files_directory_path() / "expected_state" / f"{label}.json"

    # TODO: Validate
    def _import_files(self, session: Session) -> None:
        """Put the stored files in place as of `IMPORT_TIME`.

        Frozen because this is also where a plugin's sources are initialized,
        and a source dated by the clock the machine happened to be at is a
        record that is different on every run.
        """
        with (
            freeze_time(IMPORT_TIME),
            patch.object(database_module, "stored_file_record", _dated_file_record),
        ):
            super()._import_files(session)

    # TODO: Validate
    def _initialize_import_data(self, session: Session) -> None:
        """Download whatever the test needs that is not stored yet.

        Left on the real clock, unlike everything else here, because what this
        run stores is shared with every other test that reaches for the same
        file and a file dated by this test's frozen clock would say it was
        downloaded on a day it was not. What the test compares is written by the
        test itself the first time it runs, so nothing is recorded here.
        """
        self._import_url(session)

    # TODO: Validate
    def state_dump(self, session: Session) -> dict[str, Any]:
        """Return the whole database as the two runs of a test compare it."""
        plugins = self.select_plugins_with_children(session)
        return {
            "plugins": [_dump_record(plugin) for plugin in plugins],
            "canonical_shows": [
                _dump_record(canonical_show)
                for canonical_show in self.select_canonical_shows_with_children(session)
            ],
            "canonical_links": collect_canonical_links(plugins),
        }

    # TODO: Validate
    def assert_state(self, session: Session, label: str) -> None:
        """Compare the database against what `label` recorded, recording it if it has not.

        The first run writes what it found and fails, because a recording that
        nothing has looked at is not an expectation yet - it is only whatever
        the code did that day, and a test that passed on it would be saying the
        code agrees with itself.
        """
        path = self.expected_state_path(label)
        actual = json.dumps(self.state_dump(session), indent=2)

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            pytest.fail(f"Recorded the state at {path}. Check it, then run again.")

        expected = path.read_text(encoding="utf-8")
        if expected == actual:
            return

        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(path),
                tofile="actual",
                lineterm="",
            ),
        )
        pytest.fail(f"The database is not what {path} recorded.\n{diff}")

    # TODO: Validate
    def import_url(self, session: Session) -> None:
        """Import the test's URL as of `IMPORT_TIME`."""
        with freeze_time(IMPORT_TIME):
            self._import_url(session)

    # TODO: Validate
    def update_all(
        self,
        session: Session,
        entities: Sequence[Plugin | Show | Season | Episode],
    ) -> None:
        """Update every one of `entities` as of `UPDATE_TIME`.

        Every record of a kind is updated rather than one picked at random,
        because a test that compares against a saved dump has to do the same
        thing every time it runs, and because updating all of them is what says
        an update leaves the records it is not for alone.
        """
        with freeze_time(UPDATE_TIME), mock_update(), log_stats(self):
            for entity in entities:
                assert entity.data_timestamp
                entity.update_at = entity.data_timestamp + timedelta(seconds=1)
                self._get_update_function(session, entity)()
            session.flush()

    # TODO: Validate
    def all_shows(self, session: Session) -> list[Show]:
        """Every live show of every plugin, in the order their keys put them in."""
        return [
            show
            for plugin in self.select_plugins_with_children(session)
            for source in sorted(plugin.sources, key=lambda source: source.key)
            for show in sorted(source.shows, key=lambda show: show.key)
            if show.deleted_at is None
        ]

    # TODO: Validate
    def all_seasons(self, session: Session) -> list[Season]:
        """Every live season of every plugin, in the order their keys put them in."""
        return [
            season
            for show in self.all_shows(session)
            for season in sorted(show.seasons, key=lambda season: season.key)
            if season.deleted_at is None
        ]

    # TODO: Validate
    def all_episodes(self, session: Session) -> list[Episode]:
        """Every live episode of every plugin, in the order their keys put them in."""
        return [
            episode
            for season in self.all_seasons(session)
            for episode in sorted(season.episodes, key=lambda episode: episode.key)
            if episode.deleted_at is None
        ]


# TODO: Validate
class ImportURLTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that importing a URL leaves the database as it was recorded."""

    # TODO: Validate
    def test_import_url(self, session_with_files: Session) -> None:
        with log_stats(self):
            self.import_url(session_with_files)
        self.assert_state(session_with_files, "import_url")


# TODO: Validate
class UpdateShowTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every show leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_show(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        self.update_all(session_with_files, self.all_shows(session_with_files))
        self.assert_state(session_with_files, "update_show")


# TODO: Validate
class UpdateSeasonTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every season leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_season(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        self.update_all(session_with_files, self.all_seasons(session_with_files))
        self.assert_state(session_with_files, "update_season")


# TODO: Validate
class UpdateEpisodeTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every episode leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_episode(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        self.update_all(session_with_files, self.all_episodes(session_with_files))
        self.assert_state(session_with_files, "update_episode")


# TODO: Validate
class StandardTestsV2[PluginT: BasePlugin](
    ImportURLTestsV2[PluginT],
    UpdateShowTestsV2[PluginT],
    UpdateSeasonTestsV2[PluginT],
    UpdateEpisodeTestsV2[PluginT],
):
    """The standard set of tests for a plugin, with the clock fixed throughout."""
