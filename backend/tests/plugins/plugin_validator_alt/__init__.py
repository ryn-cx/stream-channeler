# TODO: Validate
"""Plugin tests whose clock is fixed and whose check is one recorded dump.

The same tests the existing validator runs, checked a different way. Rules about
how a value should move are what a test needs when it cannot say what the value
will be. Fixing the clock takes that away: an import happens on the 1st of
January and an update the day after, every file is served from the same store
the existing validator keeps and is read as though it arrived with the import,
and the only thing left that a run generates afresh is a record's id, which the
dump writes as the row it points at. What a test compares is then the whole
database, bar the files table, against the dump recorded the first time it ran.
"""

import json
import os
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin import BasePlugin
from tests.plugins.plugin_validator_alt.database import (
    IMPORT_TIME,
    UPDATE_TIME,
    DatabaseMixinAlt,
)
from tests.plugins.plugin_validator_alt.log_stats import log_stats
from tests.plugins.plugin_validator_alt.state import database_json, state_diff
from tests.plugins.plugin_validator_v2.stored_files import (
    encode_name,
    mock_update,
)

FAKE_SEASON_KEY = "plugin-validator-alt-fake-season"
"""The key of the season a deletion test adds for the update to soft delete."""

FAKE_EPISODE_KEY = "plugin-validator-alt-fake-episode"
"""The key of the episode a deletion test adds for the update to soft delete."""


# TODO: Validate
class PluginValidatorAlt[PluginT: BasePlugin](DatabaseMixinAlt[PluginT]):
    """A plugin test whose clock is fixed and whose check is one recorded dump."""

    parse_url_response: object | None = None

    # Which record of each kind the tests that need one take, counted from the
    # first in the order the keys put them in. The first is what a test wants
    # unless that one says nothing worth reading - a season with a single
    # episode, a show whose episodes are all alike - and naming another here is
    # what points a test at one that does. Picking by key order rather than at
    # random is what lets the run be compared against a recording at all.
    source_index: int = 0
    show_index: int = 0
    season_index: int = 0
    episode_index: int = 0

    # TODO: Validate
    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        """Run a test once per URL the test class declares."""
        if "url_variant" in metafunc.fixturenames:
            metafunc.parametrize("url_variant", self._url_variants())

    # TODO: Validate
    @pytest.fixture
    def url_variant(self) -> str:
        pytest.skip("No URL variants defined")

    # TODO: Validate
    def assert_state(self, session: Session, label: str) -> None:
        """Compare the whole database against what `label` recorded."""
        session.flush()
        self.assert_recorded(label, database_json(session))

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
        dump is removed once a run matches again, since a file left behind from
        a failure that has been fixed only says the test is still failing.
        """
        path = self.expected_state_path(label)
        incorrect_path = self.incorrect_state_path(label)

        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            pytest.fail(f"Recorded the dump at {path}. Check it, then run again.")

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
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        """Import the test's URL as of `IMPORT_TIME`."""
        with freeze_time(IMPORT_TIME):
            return self._import_url(session, url, force=force)

    # TODO: Validate
    def update(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> None:
        """Update `entity` as of `UPDATE_TIME`."""
        with freeze_time(UPDATE_TIME), mock_update():
            self._update(session, entity)
            session.flush()

    # TODO: Validate
    def _update(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> None:
        """Run the update the plugin that owns `entity` has for it."""
        assert entity.data_timestamp
        entity.update_at = entity.data_timestamp + timedelta(seconds=1)
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
    def all_sources(self, session: Session) -> list[Source]:
        """Every live source of every plugin, in the order their keys put them in."""
        return [
            source
            for plugin in self.select_plugins_with_children(session)
            for source in sorted(plugin.sources, key=lambda source: source.key)
            if source.deleted_at is None
        ]

    # TODO: Validate
    def all_shows(self, session: Session) -> list[Show]:
        """Every live show of every plugin, in the order their keys put them in."""
        return [
            show
            for source in self.all_sources(session)
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
    def selected_source(self, session: Session) -> Source:
        """Return the source a test that works on one takes.

        The existing validator picks one at random, which a test comparing
        against a recorded dump cannot do, so the one the class names is taken
        instead and the first is what it names unless it says otherwise.
        """
        return self.all_sources(session)[self.source_index]

    # TODO: Validate
    def selected_show(self, session: Session) -> Show:
        """Return the show a test that works on one takes."""
        return self.all_shows(session)[self.show_index]

    # TODO: Validate
    def selected_season(self, session: Session) -> Season:
        """Return the season a test that works on one takes."""
        return self.all_seasons(session)[self.season_index]

    # TODO: Validate
    def selected_episode(self, session: Session) -> Episode:
        """Return the episode a test that works on one takes."""
        return self.all_episodes(session)[self.episode_index]

    # TODO: Validate
    def fake_season(self, show: Show) -> Season:
        """Build a season `show` does not have, for an update to soft delete.

        Written out in full rather than generated, because a randomly built
        record is a different record on every run and so a different dump.
        """
        return Season(
            key=FAKE_SEASON_KEY,
            name="Plugin Validator Alt Fake Season",
            url="https://example.com/fake-season",
            season_number=9999,
            sort_order=9999,
            show_id=show.id,
            data_timestamp=tz_datetime.now(),
            deleted_at=tz_datetime.now(),
        )

    # TODO: Validate
    def fake_episode(self, season: Season) -> Episode:
        """Build an episode `season` does not have, for an update to soft delete.

        `plugin_key` is set here because an import is what usually writes it and
        nothing imported this row.
        """
        return Episode(
            key=FAKE_EPISODE_KEY,
            name="Plugin Validator Alt Fake Episode",
            url="https://example.com/fake-episode",
            episode_number=9999,
            sort_order=9999,
            duration=1,
            season_id=season.id,
            plugin_key=season.show.source.plugin.key,
            data_timestamp=tz_datetime.now(),
            deleted_at=tz_datetime.now(),
        )

    # TODO: Validate
    def _initialize_import_data(self, session: Session) -> None:
        """Import the URL so every file it reaches for is stored."""
        if self.invalid_url:
            with pytest.raises(InvalidURLError):
                self._import_url(session)
            return
        self._import_url(session)

    # TODO: Validate
    def _initialize_extra_files(self, session: Session) -> None:
        """Store the files that only an update reaches for.

        A test's data is recorded by importing a URL, which never asks for the
        files a plugin only reads when checking an existing record for changes.
        Left unstored, those are what an update test has to reach the network
        for, which it is not allowed to do.
        """

    # TODO: Validate
    @pytest.mark.enable_socket
    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Records/refreshes test data locally; never runs on CI.",
    )
    def test__initialize_test_data(self, session_with_files: Session) -> None:
        """Download and store every file the test class needs.

        Left on the real clock, unlike every other test here, because what this
        run stores is shared with every test that reaches for the same file -
        the existing validator's included - and a file dated by a frozen clock
        would say it was downloaded on a day it was not. What the files already
        in place are dated at is no matter here: this run compares nothing, and
        a file it reads as out of date is one it reaches for again and is served
        out of the store.

        Nothing is recorded here but the files. What the other tests compare
        against is written by those tests the first time they run.
        """
        try:
            if self.url:
                self._initialize_import_data(session_with_files)
                self._initialize_extra_files(session_with_files)
        finally:
            # Written even when the run failed, so the files it did reach are
            # recorded rather than downloaded again by the next run.
            self._export_files_manifest(session_with_files)


# TODO: Validate
class ImportURLTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that importing a URL leaves the database as it was recorded."""

    # TODO: Validate
    def test_import_url(self, session_with_files: Session) -> None:
        if not self.url or self.invalid_url:
            pytest.skip()

        with log_stats(self):
            results = self.import_url(session_with_files)
        self.assert_import_url_results(results, "import_url_results")
        self.assert_state(session_with_files, "import_url")


# TODO: Validate
class ImportURLVariantTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
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
class InvalidImportURLTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that importing an invalid URL raises InvalidURLError."""

    # TODO: Validate
    def test_import_url(self, session_with_files: Session) -> None:
        if not self.url:
            pytest.skip()

        with log_stats(self), pytest.raises(InvalidURLError):
            self.import_url(session_with_files)


# TODO: Validate
class ImportExistingURLTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that re-importing a URL leaves the database where the first import put it.

    Compared against the dump the import test recorded rather than against one
    of its own, because what a second import must leave behind is what the first
    one did and nothing else.
    """

    # TODO: Validate
    def test_import_existing_url(self, session_with_files: Session) -> None:
        if not self.url or self.invalid_url:
            pytest.skip()

        self.import_url(session_with_files)
        with log_stats(self):
            self.import_url(session_with_files)
        self.assert_state(session_with_files, "import_url")


# TODO: Validate
class UpdatePluginTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that updating the plugin refreshes what the plugin itself holds.

    Kept out of `UpdateTestsAlt` because most plugins hold their media under a
    `Source` and have nothing of their own for this to reach. It is for a plugin
    whose records hang off the plugin row rather than off a source.
    """

    # TODO: Validate
    def test_update_plugin(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        plugin = self.select_plugin_with_children(session_with_files)
        with log_stats(self):
            self.update(session_with_files, plugin)
        self.assert_state(session_with_files, "update_plugin")


# TODO: Validate
class UpdateSourceTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that updating a source propagates upstream changes."""

    # TODO: Validate
    def _create_source_update_entry(
        self,
        plugin_instance: PluginT,
        source: Source,
        timestamp: datetime,
    ) -> None:
        """Fabricate an upstream update signal for `source` at `timestamp`.

        Each plugin writes whatever fake file(s) make `update_source` see a
        pending refresh for the given source keyed at the given timestamp.
        """
        raise NotImplementedError

    # TODO: Validate
    def test_update_source(self, session_with_files: Session) -> None:
        if self.invalid_url or not self.url:
            pytest.skip()

        self.import_url(session_with_files)
        source = self.selected_source(session_with_files)
        timestamp = UPDATE_TIME + timedelta(minutes=1)
        with freeze_time(UPDATE_TIME):
            self._create_source_update_entry(self.imported_plugin, source, timestamp)
            # Seed update_at later than the pending air_date so set_update_at
            # overwrites it with the earlier value.
            for show in source.shows:
                show.update_at = timestamp + timedelta(minutes=1)
                for season in show.seasons:
                    if season.update_at:
                        season.update_at = timestamp + timedelta(minutes=1)

        with log_stats(self):
            self.update(session_with_files, source)
        self.assert_state(session_with_files, "update_source")


# TODO: Validate
class UpdateShowTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that updating a show leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_show(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update(session_with_files, self.selected_show(session_with_files))
        self.assert_state(session_with_files, "update_show")


# TODO: Validate
class UpdateSeasonTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that updating a season leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_season(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update(session_with_files, self.selected_season(session_with_files))
        self.assert_state(session_with_files, "update_season")


# TODO: Validate
class UpdateEpisodeTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that updating an episode leaves the database as it was recorded."""

    # TODO: Validate
    def test_update_episode(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        with log_stats(self):
            self.update(session_with_files, self.selected_episode(session_with_files))
        self.assert_state(session_with_files, "update_episode")


# TODO: Validate
class DeletedEpisodeTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that a fake episode gets soft deleted during update_season."""

    # TODO: Validate
    def test_deleted_episode(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        season = self.selected_season(session_with_files)

        with freeze_time(UPDATE_TIME):
            fake_episode = self.fake_episode(season)
            season.episodes.append(fake_episode)
            fake_episode.soft_undelete()
            session_with_files.flush()

        # `log_stats` is entered before the clock is held, because a frozen clock
        # is what its timer reads too and a run measured against one takes no
        # time at all. The flush is held inside, because what an update wrote is
        # stamped when it reaches the database and not when it was worked out,
        # and a row left to be flushed by the comparison is a row stamped by the
        # clock the machine happened to be at.
        with log_stats(self), freeze_time(UPDATE_TIME):
            self.plugin_class(session_with_files).update_season(season=season)
            session_with_files.flush()

        self.assert_state(session_with_files, "deleted_episode")


# TODO: Validate
class DeletedSeasonTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Tests that a fake season gets soft deleted during update_show."""

    # TODO: Validate
    def test_deleted_season(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        show = self.selected_show(session_with_files)

        with freeze_time(UPDATE_TIME):
            fake_season = self.fake_season(show)
            show.seasons.append(fake_season)
            fake_season.soft_undelete()
            session_with_files.flush()

        with log_stats(self), freeze_time(UPDATE_TIME):
            self.plugin_class(session_with_files).update_show(show=show)
            session_with_files.flush()

        self.assert_state(session_with_files, "deleted_season")


# TODO: Validate
class DeletedEpisodeUpdateShowTestsAlt[PluginT: BasePlugin](
    PluginValidatorAlt[PluginT],
):
    """Tests that a fake episode in an existing season is soft deleted by update_show."""

    # TODO: Validate
    def test_deleted_episode_update_show(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        season = self.selected_season(session_with_files)
        show = season.show

        with freeze_time(UPDATE_TIME):
            fake_episode = self.fake_episode(season)
            season.episodes.append(fake_episode)
            fake_episode.soft_undelete()
            session_with_files.flush()

        with log_stats(self), freeze_time(UPDATE_TIME):
            self.plugin_class(session_with_files).update_show(show=show)
            session_with_files.flush()

        self.assert_state(session_with_files, "deleted_episode_update_show")


# TODO: Validate
class DeletedSeasonWithEpisodeTestsAlt[PluginT: BasePlugin](
    PluginValidatorAlt[PluginT],
):
    """Tests that a fake season and its fake episode are soft deleted by update_show."""

    # TODO: Validate
    def test_deleted_season_with_episode(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        show = self.selected_show(session_with_files)

        with freeze_time(UPDATE_TIME):
            fake_season = self.fake_season(show)
            show.seasons.append(fake_season)
            fake_season.episodes.append(self.fake_episode(fake_season))
            fake_season.soft_undelete()
            session_with_files.flush()

        with log_stats(self), freeze_time(UPDATE_TIME):
            self.plugin_class(session_with_files).update_show(show=show)
            session_with_files.flush()

        self.assert_state(session_with_files, "deleted_season_with_episode")


# TODO: Validate
class AllUpdatesTestsAlt[PluginT: BasePlugin](PluginValidatorAlt[PluginT]):
    """Exhaustive test that updates every entity on its own."""

    # TODO: Validate
    @pytest.mark.skip(reason="Exhaustive test - run manually")
    def test_all_updates(self, session_with_files: Session) -> None:
        self.import_url(session_with_files)
        entities: list[Show | Season | Episode] = [
            *self.all_shows(session_with_files),
            *self.all_seasons(session_with_files),
            *self.all_episodes(session_with_files),
        ]
        for entity in entities:
            label = f"all_updates_{type(entity).__name__}_{encode_name(entity.key)}"
            self.update(session_with_files, entity)
            self.assert_state(session_with_files, label)
            session_with_files.rollback()


# TODO: Validate
class URLTestsAlt[PluginT: BasePlugin](
    ImportURLVariantTestsAlt[PluginT],
    ImportURLTestsAlt[PluginT],
    ImportExistingURLTestsAlt[PluginT],
):
    """All URL-related tests: importing and re-importing."""


# TODO: Validate
class UpdateTestsAlt[PluginT: BasePlugin](
    UpdateShowTestsAlt[PluginT],
    UpdateSeasonTestsAlt[PluginT],
    UpdateEpisodeTestsAlt[PluginT],
):
    """All entity update tests."""


# TODO: Validate
class DeletionTestsAlt[PluginT: BasePlugin](
    DeletedEpisodeTestsAlt[PluginT],
    DeletedSeasonTestsAlt[PluginT],
    DeletedEpisodeUpdateShowTestsAlt[PluginT],
    DeletedSeasonWithEpisodeTestsAlt[PluginT],
):
    """All soft-deletion tests."""


# TODO: Validate
class StandardTestsAlt[PluginT: BasePlugin](
    URLTestsAlt[PluginT],
    UpdateTestsAlt[PluginT],
    DeletionTestsAlt[PluginT],
    AllUpdatesTestsAlt[PluginT],
):
    """The standard set of tests for a plugin with URL import support."""


# TODO: Validate
class InvalidURLValidatorAlt[PluginT: BasePlugin](
    InvalidImportURLTestsAlt[PluginT],
    PluginValidatorAlt[PluginT],
):
    """Validator for plugins with invalid URLs that should raise errors."""

    invalid_url = True
