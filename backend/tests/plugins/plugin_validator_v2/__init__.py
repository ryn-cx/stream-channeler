# TODO: Validate
"""Plugin tests whose clock is fixed and whose check is one recorded dump."""

import json
import os
from collections.abc import Sequence
from datetime import timedelta

import pytest
from freezegun import freeze_time
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin import BasePlugin
from tests.plugins.plugin_validator_v2.database import DatabaseMixin
from tests.plugins.plugin_validator_v2.log_stats import log_stats
from tests.plugins.plugin_validator_v2.state import state_diff, state_json
from tests.plugins.plugin_validator_v2.stored_files import (
    IMPORT_TIME,
    UPDATE_TIME,
    mock_update,
)


# TODO: Validate
class PluginValidatorV2[PluginT: BasePlugin](DatabaseMixin[PluginT]):
    """A plugin test whose clock is fixed and whose check is one recorded dump.

    Rules about how a value should move are what a test needs when it cannot say
    what the value will be. Fixing the clock takes that away: an import happens
    on the 1st of January and an update a month later, every file is read as
    though it arrived with the import, and the only thing left that a run
    generates afresh is a record's id, which the dump leaves out. What a test
    compares is then the whole database against the dump recorded the first time
    it ran.
    """

    # TODO: Validate
    def state_json(self, session: Session) -> str:
        """Return the whole database as the text a test compares."""
        return state_json(
            self.select_plugins_with_children(session),
            self.select_canonical_shows_with_children(session),
            self.select_users(session),
        )

    # TODO: Validate
    def assert_state(self, session: Session, label: str) -> None:
        """Compare the database against what `label` recorded."""
        self.assert_recorded(label, self.state_json(session))

    # TODO: Validate
    def assert_import_url_results(
        self,
        results: list[URLImportResult],
        label: str,
    ) -> None:
        """Compare what an import said it produced against what `label` recorded."""
        self.assert_recorded(
            label,
            json.dumps(self.simplify_import_url_results(results), indent=2),
        )

    # TODO: Validate
    def assert_recorded(self, label: str, actual: str) -> None:
        """Compare `actual` against what `label` recorded, recording it if it has not.

        The first run writes what it found and fails, because a recording that
        nothing has looked at is not an expectation yet - it is only whatever
        the code did that day, and a test that passed on it would be saying the
        code agrees with itself.

        A run that does not match writes what it produced beside what was
        expected, so the two can be read against each other with whatever tool
        reads a file rather than only as the diff in the failure. The written
        state is removed once a run matches again, since a file left behind from
        a failure that has been fixed only says the test is still failing.
        """
        path = self.expected_state_path(label)
        incorrect_path = self.incorrect_state_path(label)

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            pytest.fail(f"Recorded the state at {path}. Check it, then run again.")

        expected = path.read_text(encoding="utf-8")
        if expected == actual:
            incorrect_path.unlink(missing_ok=True)
            return

        incorrect_path.parent.mkdir(parents=True, exist_ok=True)
        incorrect_path.write_text(actual, encoding="utf-8")
        pytest.fail(
            f"This run is not what {path} recorded.\n"
            f"What this run produced is at {incorrect_path}.\n"
            f"{state_diff(expected, actual)}",
        )

    # TODO: Validate
    def import_url(
        self,
        session: Session,
        url: str | None = None,
    ) -> list[URLImportResult]:
        """Import the test's URL as of `IMPORT_TIME`."""
        with freeze_time(IMPORT_TIME):
            return self._import_url(session, url)

    # TODO: Validate
    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Run a test once per URL the test class declares."""
        if "url_variant" in metafunc.fixturenames:
            metafunc.parametrize("url_variant", self._url_variants())

    # TODO: Validate
    def update_all(
        self,
        session: Session,
        entities: Sequence[Plugin | Source | Show | Season | Episode],
    ) -> None:
        """Update every one of `entities` as of `UPDATE_TIME`.

        Every record of a kind is updated rather than one picked at random,
        because a test that compares against a recorded dump has to do the same
        thing every time it runs, and because updating all of them is what says
        an update leaves the records it is not for alone.
        """
        with freeze_time(UPDATE_TIME), mock_update():
            for entity in entities:
                assert entity.data_timestamp
                entity.update_at = entity.data_timestamp + timedelta(seconds=1)
                self._update(session, entity)
            session.flush()

    # TODO: Validate
    def _update(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> None:
        """Run the update the plugin that owns `entity` has for it."""
        owner = self.owning_plugin(session, entity)
        match entity:
            case Plugin() as plugin:
                owner.update_plugin(plugin=plugin)
            case Source() as source:
                owner.update_source(source=source)
            case Show() as show:
                owner.update_show(show=show)
            case Season() as season:
                owner.update_season(season)
            case Episode() as episode:
                owner.update_episode(episode)

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
    @pytest.mark.enable_socket
    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Records/refreshes test data locally; never runs on CI.",
    )
    def test__initialize_test_data(self, session_with_files: Session) -> None:
        """Download and store every file the test class needs.

        Left on the real clock, unlike every other test here, because what this
        run stores is shared with every test that reaches for the same file and
        a file dated by a frozen clock would say it was downloaded on a day it
        was not. What the other tests compare against is written by those tests
        the first time they run, so nothing is recorded here but the files.
        """
        try:
            self._import_url(session_with_files)
        finally:
            # Written even when the run failed, so the files it did reach are
            # recorded rather than downloaded again by the next run.
            self._export_files_manifest(session_with_files)


# TODO: Validate
class ImportURLTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that importing a URL leaves the database as it was recorded."""

    # TODO: Validate
    def test_import_url(self, session_with_files: Session) -> None:
        with log_stats(self):
            results = self.import_url(session_with_files)
        self.assert_import_url_results(results, "import_url_results")
        self.assert_state(session_with_files, "import_url")


# TODO: Validate
class ImportURLVariantTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that every domain and path a URL can be written as imports the same.

    Checked against what the import itself said it produced rather than against
    the whole database, because what a variant can get wrong is which records
    the URL names, and the records themselves are what the import test covers.
    Every variant is compared against the one recording, that being what says
    the variants agree rather than only that each is what it was last time.
    """

    # TODO: Validate
    def test_import_url_variants(
        self,
        session_with_files: Session,
        url_variant: str,
    ) -> None:
        with log_stats(self):
            results = self.import_url(session_with_files, url_variant)
        self.assert_import_url_results(results, "import_url_results")


# TODO: Validate
class UpdateShowTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every show leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_show(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update_all(session_with_files, self.all_shows(session_with_files))
        self.assert_state(session_with_files, "update_show")


# TODO: Validate
class UpdateSeasonTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every season leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_season(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update_all(session_with_files, self.all_seasons(session_with_files))
        self.assert_state(session_with_files, "update_season")


# TODO: Validate
class UpdateEpisodeTestsV2[PluginT: BasePlugin](PluginValidatorV2[PluginT]):
    """Tests that updating every episode leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_episode(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update_all(session_with_files, self.all_episodes(session_with_files))
        self.assert_state(session_with_files, "update_episode")


# TODO: Validate
class StandardTestsV2[PluginT: BasePlugin](
    ImportURLTestsV2[PluginT],
    ImportURLVariantTestsV2[PluginT],
    UpdateShowTestsV2[PluginT],
    UpdateSeasonTestsV2[PluginT],
    UpdateEpisodeTestsV2[PluginT],
):
    """The standard set of tests for a plugin, with the clock fixed throughout."""
