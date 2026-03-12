# TODO: Validate
import random
from collections.abc import Callable

import pytest
import yaml
from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.models import Plugin
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.utils import tz_datetime
from tests.plugins.plugin_validator.database import DatabaseMixin
from tests.plugins.plugin_validator.log_stats import log_stats
from tests.plugins.plugin_validator.mocks import (
    block_downloads,
    disable_ip_validation,
    mock_update,
    track_downloads,
)
from tests.plugins.plugin_validator.validator import Validator
from tests.utils.utils import build_random_model


class PluginValidator(DatabaseMixin):
    # region Configuration

    plugin_class: type[BasePlugin]
    url: str
    skip_update_tests = False
    skip_test_import_url = False
    skip_test_import_existing_url = False
    skip_test_update_source = False
    skip_test_update_show = False
    skip_test_update_season = False
    skip_test_update_episode = False
    invalid_url = False

    # endregion Configuration

    # region Validation

    def _get_detached_plugin(self, db: Session) -> Plugin:
        """Return a detached copy of the plugin to use for validation."""
        plugin = self.select_plugin_with_children(db)
        dumped = self._dump_model(plugin)
        return self._load_model(Plugin, dumped)

    def _validate_plugin(
        self,
        db: Session,
        original_plugin: Plugin,
        config: Validator,
    ) -> None:
        """Validate that the current database state matches the original plugin."""
        config.validate(original_plugin, self._get_detached_plugin(db))

    def _base_validator(self) -> Validator:
        return Validator().changed(Plugin, "user_id")

    def _import_url_validator(self) -> Validator:
        return (
            self._base_validator()
            # These will always change because they are based on when the import occurs.
            .incremented_all("created_at", "modified_at")
            .incremented(Plugin, "data_timestamp")
            # These will all change because ids are randomly generated.
            .changed_all("id")
            .changed(Source, "plugin_id")
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

    # endregion Validation

    # region Get Random

    @staticmethod
    def _random_show(results: list[URLImportResult]) -> Show:
        shows = [result.show for result in results]
        if not shows:
            pytest.fail("No shows found.")
        return random.choice(shows)  # noqa: S311

    @staticmethod
    def _random_season(results: list[URLImportResult]) -> Season:
        seasons = [season for result in results for season in result.show.seasons]
        if not seasons:
            pytest.fail("No seasons found.")
        return random.choice(seasons)  # noqa: S311

    @staticmethod
    def _random_episode(results: list[URLImportResult]) -> Episode:
        episodes = [
            episode
            for result in results
            for season in result.show.seasons
            for episode in season.episodes
        ]
        if not episodes:
            pytest.fail("No episodes found.")
        return random.choice(episodes)  # noqa: S311

    # endregion Get Random

    # region Tests

    def test__initialize_test_data(
        self,
        db_with_files: Session,
    ) -> None:
        """Downloads and saves all of the data required for the tests.

        On first run this will download files and export them. Subsequent runs
        verify that all files are served from cache (no downloads occur).
        """
        if self.invalid_url:
            pytest.skip()
        files_already_cached = self.combined_files_path().exists()
        try:
            with disable_ip_validation(), track_downloads() as downloaded:
                self._import_url(db_with_files)
            self._export_all_files(db_with_files)
        # If importing fails the downloaded files can still be dumped for analysis, but
        # the verification file should not be dumped because it is not valid.
        except Exception:
            self._export_database_files(db_with_files)
            raise

        if files_already_cached and downloaded:
            pytest.fail(f"Files were downloaded during import: {downloaded}")

    def test_import_url(self, db_with_files: Session) -> None:
        if self.skip_test_import_url:
            pytest.skip()

        if self.invalid_url:
            with pytest.raises(InvalidURLError):
                self._import_url(db_with_files)
            return

        with block_downloads(), log_stats(self):
            self._import_url(db_with_files)
            db_with_files.flush()

        # This is the only test that compares with the validation file because the goal
        # of this test is to make sure the imported data matches the expected data. The
        # goal of the other tests is to make sure the data updates correctly.
        verification_content = self.verification_file_path().read_text()
        # S506 - It is safe to import using fullLoader because the data was written
        # by the test suite.
        verification_data = yaml.load(verification_content, Loader=yaml.Loader)  # noqa: S506

        original_plugin = self._load_model(Plugin, verification_data)
        validator = self._import_url_validator()
        self._validate_plugin(db_with_files, original_plugin, validator)

    def test_import_existing_url(self, db_with_url: Session) -> None:
        """Test importing a URL that already exists."""
        if self.invalid_url or self.skip_test_import_existing_url:
            pytest.skip()
        original_plugin = self._get_detached_plugin(db_with_url)
        with log_stats(self), block_downloads():
            self.plugin_class(db_with_url, url=self.url).import_url(self.url)

        validator = self._existing_url_validator()
        self._validate_plugin(db_with_url, original_plugin, validator)

    def _test_update(
        self,
        db_with_url: Session,
        *,
        skip: bool,
        get_random: Callable[[list[URLImportResult]], Show | Season | Episode],
    ) -> None:
        """Pick a random entity from the import results and validate updating it."""
        if self.invalid_url or self.skip_update_tests or skip:
            pytest.skip()
        original_plugin = self._get_detached_plugin(db_with_url)
        results = self._import_url(db_with_url)
        entity = get_random(results)
        self._update_and_validate(db_with_url, original_plugin, entity)

    def test_update_show(self, db_with_url: Session) -> None:
        """Update a random show and validate the data."""
        self._test_update(
            db_with_url,
            skip=self.skip_test_update_show,
            get_random=self._random_show,
        )

    def test_update_season(self, db_with_url: Session) -> None:
        """Update a random season and validate the data."""
        self._test_update(
            db_with_url,
            skip=self.skip_test_update_season,
            get_random=self._random_season,
        )

    def test_update_episode(self, db_with_url: Session) -> None:
        """Update a random episode and validate the data."""
        self._test_update(
            db_with_url,
            skip=self.skip_test_update_episode,
            get_random=self._random_episode,
        )

    def _update_and_validate(
        self,
        db: Session,
        original_plugin: Plugin,
        entity: Show | Season | Episode,
        validator: Validator | None = None,
    ) -> None:
        key = entity.key
        data_timestamp = entity.data_timestamp
        update_at = tz_datetime.now()

        match entity:
            case Show() as show:
                build_random_model(
                    ShowInput,
                    key=key,
                    data_timestamp=data_timestamp,
                    update_at=update_at,
                ).upsert(show.source, show)
                validator = validator or self._update_show_validator(show)

                def update() -> None:
                    self.plugin_class(db, show=show).update_show(show=show)

            case Season() as season:
                build_random_model(
                    SeasonInput,
                    key=key,
                    data_timestamp=data_timestamp,
                    update_at=update_at,
                ).upsert(season.show, season)
                validator = validator or self._update_season_validator(season)

                def update() -> None:
                    self.plugin_class(db, season=season).update_season(season)

            case Episode() as episode:
                build_random_model(
                    EpisodeInput,
                    key=key,
                    data_timestamp=data_timestamp,
                    update_at=update_at,
                ).upsert(episode.season, episode)
                validator = validator or self._update_episode_validator(episode)

                def update() -> None:
                    self.plugin_class(db, episode=episode).update_episode(episode)

        with mock_update(self.files_directory_path()), log_stats(self):
            update()
            db.flush()

        msg = f"Failed updating: {entity}"
        try:
            self._validate_plugin(db, original_plugin, validator)
        except AssertionError as e:
            raise AssertionError(msg) from e

    @pytest.mark.skip(reason="Exhaustive test - run manually")
    def test_all_updates(self, db_with_url: Session) -> None:
        original_plugin = self._get_detached_plugin(db_with_url)
        plugin = self.select_plugin_with_children(db_with_url)

        for source in plugin.sources:
            for show in source.shows:
                if show.data_timestamp:
                    self._update_and_validate(db_with_url, original_plugin, show)
                    db_with_url.rollback()
                for season in show.seasons:
                    self._update_and_validate(db_with_url, original_plugin, season)
                    db_with_url.rollback()
                    for episode in season.episodes:
                        self._update_and_validate(db_with_url, original_plugin, episode)
                        db_with_url.rollback()


class InvalidURLValidator(PluginValidator):
    invalid_url = True
