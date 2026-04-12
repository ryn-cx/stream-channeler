# TODO: Validate
import json
import random
from collections.abc import Callable, Sequence
from contextlib import nullcontext
from datetime import timedelta
from typing import Any

import pytest
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.utils.abstract_plugin import (
    InvalidURLError,
    PluginSearchResults,
    URLImportResult,
)
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from tests.plugins.plugin_validator.database import DatabaseMixin
from tests.plugins.plugin_validator.log_stats import log_stats
from tests.plugins.plugin_validator.mocks import (
    block_downloads,
    mock_update,
    track_downloads,
)
from tests.plugins.plugin_validator.validator import Validator
from tests.utils.utils import build_random_model

# region Base


class PluginValidator[PluginT: BasePlugin](DatabaseMixin[PluginT]):
    """Base class with shared configuration, validation helpers, and data initialization."""

    plugin_class: type[PluginT]
    url: str | None = None
    parse_url_response: object | None = None
    url_path_patterns: tuple[str, ...] = ()
    invalid_url = False
    search_query: str | None = None

    # region Validation

    def get_detached_plugin(self, db: Session) -> Plugin:
        """Return a detached copy of the plugin to use for validation."""
        plugin = self.select_plugin_with_children(db)
        dumped = self._dump_model(plugin)
        return self._load_model(Plugin, dumped)

    def validate_plugin(
        self,
        db: Session,
        original_plugin: Plugin,
        config: Validator,
    ) -> None:
        """Validate that the current database state matches the original plugin."""
        config.validate(original_plugin, self.get_detached_plugin(db))

    def import_url_validator(self) -> Validator:
        return (
            Validator()
            .changed(Plugin, "user_id")
            .incremented_all("created_at", "modified_at")
            .changed_all("id")
            .changed(Source, "plugin_id")
            .changed(Show, "source_id")
            .changed(Season, "show_id")
            .changed(Episode, "season_id")
        )

    def existing_url_validator(self) -> Validator:
        return Validator()

    def generic_update_validator(
        self,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Validator:
        return Validator().incremented(entity.id, "modified_at", "data_timestamp")

    def update_plugin_validator(self, db: Session, plugin: Plugin) -> Validator:  # noqa: ARG002
        return self.generic_update_validator(plugin)

    def update_source_validator(self, source: Source) -> Validator:
        return self.generic_update_validator(source)

    def update_show_validator(self, show: Show) -> Validator:
        return self.generic_update_validator(show)

    def update_season_validator(self, season: Season) -> Validator:
        return self.generic_update_validator(season)

    def update_episode_validator(self, episode: Episode) -> Validator:
        return self.generic_update_validator(episode)

    def generic_deleted_validator(
        self,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Validator:
        return (
            Validator()
            .incremented(entity.id, "deleted_at")
            .incremented(entity.id, "modified_at")
        )

    def deleted_season_validator(self, season: Season) -> Validator:
        return self.generic_deleted_validator(season)

    def deleted_episode_validator(self, episode: Episode) -> Validator:
        return self.generic_deleted_validator(episode)

    # endregion Validation

    # region Get Random

    @staticmethod
    def get_random_source(results: list[URLImportResult]) -> Source:
        sources = [result.show.source for result in results]
        return random.choice(sources)  # noqa: S311

    @staticmethod
    def get_random_show(results: list[URLImportResult]) -> Show:
        shows = [result.show for result in results]
        return random.choice(shows)  # noqa: S311

    @staticmethod
    def get_random_season(results: list[URLImportResult]) -> Season:
        seasons = [season for result in results for season in result.show.seasons]
        return random.choice(seasons)  # noqa: S311

    @staticmethod
    def get_random_episode(results: list[URLImportResult]) -> Episode:
        episodes = [
            episode
            for result in results
            for season in result.show.seasons
            for episode in season.episodes
        ]
        return random.choice(episodes)  # noqa: S311

    # endregion Get Random

    # region Update Helpers

    def _randomize_entity(
        self,
        entity: Plugin | Source | Show | Season | Episode,
        static_keys: list[str] | None = None,
    ) -> None:
        """Randomize non-key fields on the entity to detect unintended overwrites."""
        data_timestamp = entity.data_timestamp
        assert data_timestamp
        update_at = tz_datetime.now()

        defaults: dict[str, Any] = {
            "key": entity.key,
            "data_timestamp": data_timestamp,
        }
        for key in static_keys or []:
            defaults[key] = getattr(entity, key)

        parent_id_field = f"{type(entity.parent).__name__.lower()}_id"
        defaults[parent_id_field] = getattr(entity, parent_id_field)
        # update_at must be set AFTER static_keys so the plugin considers the
        # entity due for update, even when static_keys includes "update_at".
        defaults["update_at"] = update_at
        build_random_model(
            type(entity),
            **defaults,
        ).upsert(entity.parent, entity)

    def _get_update_function(
        self,
        db: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Callable[[], None]:
        """Return the appropriate plugin update function for the entity type."""
        match entity:
            case Plugin() as plugin:
                return lambda: self.plugin_class(db).update_plugin(plugin=plugin)
            case Source() as source:
                return lambda: self.plugin_class(db, source=source).update_source(
                    source=source,
                )
            case Show() as show:
                return lambda: self.plugin_class(db, show=show).update_show(show=show)
            case Season() as season:
                return lambda: self.plugin_class(db, season=season).update_season(
                    season,
                )
            case Episode() as episode:
                return lambda: self.plugin_class(db, episode=episode).update_episode(
                    episode,
                )

    def _get_validator(
        self,
        db: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Validator:
        """Return the default validator for the given entity type."""
        match entity:
            case Plugin() as plugin:
                return self.update_plugin_validator(db, plugin)
            case Source() as source:
                return self.update_source_validator(source)
            case Show() as show:
                return self.update_show_validator(show)
            case Season() as season:
                return self.update_season_validator(season)
            case Episode() as episode:
                return self.update_episode_validator(episode)

    def _update_and_validate(  # noqa: PLR0913
        self,
        db: Session,
        original_plugin: Plugin,
        entity: Plugin | Source | Show | Season | Episode,
        validator: Validator | None = None,
        *,
        use_mock_update: bool = True,
        static_keys: list[str] | None = None,
    ) -> None:
        """Randomize an entity's data and verify the update function restores it.

        Overwrites the entity's fields with random values (preserving key,
        data_timestamp, and any static_keys), sets update_at to now so the
        plugin considers it due for an update, then runs the plugin's update
        function and validates that all fields were restored correctly.
        """
        self._randomize_entity(entity, static_keys)
        validator = validator or self._get_validator(db, entity)
        update = self._get_update_function(db, entity)

        maybe_mock_wrapper = (
            mock_update(self.files_directory_path())
            if use_mock_update
            else nullcontext()
        )
        with maybe_mock_wrapper, log_stats(self):
            update()
            db.flush()

        msg = f"Failed updating: {entity}"
        try:
            self.validate_plugin(db, original_plugin, validator)
        except AssertionError as error:
            raise AssertionError(msg) from error

    # endregion Update Helpers

    # region Data Initialization

    def _initialize_import_data(
        self,
        db: Session,
        *,
        files_already_cached: bool,
    ) -> None:
        """Import URL data, always exporting files for analysis even on failure."""
        try:
            with track_downloads() as download_count:
                if self.invalid_url:
                    with pytest.raises(InvalidURLError):
                        self._import_url(db)
                else:
                    self._import_url(db)
        finally:
            self._export_database_files(db)

        if not self.invalid_url:
            self._export_verification_file(db)

        if files_already_cached and download_count:
            pytest.fail(f"Files were downloaded during import: {download_count}")

    def _initialize_search_data(
        self,
        db: Session,
        search_query: str,
        *,
        files_already_cached: bool,
    ) -> None:
        """Run a search query, exporting files for analysis on failure."""
        try:
            with track_downloads() as download_count:
                self._search(db, search_query)
        except Exception:
            self._export_database_files(db)
            raise

        if files_already_cached and download_count:
            pytest.fail(f"Files were downloaded during search: {download_count}")

    def test__initialize_test_data(
        self,
        db_with_files: Session,
    ) -> None:
        """Downloads and saves all of the data required for the tests.

        On first run this will download files and export them. Subsequent runs
        verify that all files are served from cache (no downloads occur).
        """
        files_already_cached = self.combined_files_path().exists()

        if self.url:
            self._initialize_import_data(
                db_with_files,
                files_already_cached=files_already_cached,
            )

        if self.search_query:
            self._initialize_search_data(
                db_with_files,
                self.search_query,
                files_already_cached=files_already_cached,
            )

    # endregion Data Initialization


# endregion Base

# region Individual Test Mixins


class ParseURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that parse_url returns the expected response for the canonical URL."""

    def test_parse_url(self) -> None:
        if not self.url or not self.parse_url_response:
            pytest.skip()
        assert self.plugin_class.parse_url(self.url) == self.parse_url_response


class ParseURLVariantTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that parse_url works across all domain/path pattern combinations."""

    def pytest_generate_tests(self, metafunc: pytest.Metafunc) -> None:
        if "url_variant" in metafunc.fixturenames:
            class_attrs = {
                key: value
                for key, value in vars(type(self)).items()
                if isinstance(value, str)
            }
            variants = [
                domain + pattern.format(**class_attrs)
                for domain in self.plugin_class.domains()
                for pattern in self.url_path_patterns
            ]
            metafunc.parametrize("url_variant", variants)

    @pytest.fixture
    def url_variant(self) -> str:
        pytest.skip("No URL variants defined")

    def test_parse_url_variants(self, url_variant: str) -> None:
        assert self.plugin_class.parse_url(url_variant) == self.parse_url_response


class ImportURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that importing a URL produces the expected plugin state."""

    def test_import_url(self, db_with_files: Session) -> None:
        if not self.url or self.invalid_url:
            pytest.skip()

        with block_downloads(), log_stats(self):
            self.plugin_class(db_with_files, url=self.url).import_url(self.url)

        verification_content = self.verification_file_path().read_text()
        verification_data = json.loads(verification_content)

        original_plugin = self._load_model(Plugin, verification_data)
        validator = self.import_url_validator()
        self.validate_plugin(db_with_files, original_plugin, validator)


class InvalidImportURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that importing an invalid URL raises InvalidURLError."""

    def test_import_url(self, db_with_files: Session) -> None:
        if not self.url:
            pytest.skip()

        with block_downloads(), log_stats(self), pytest.raises(InvalidURLError):
            self.plugin_class(db_with_files, url=self.url).import_url(self.url)


class ImportExistingURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that re-importing an existing URL doesn't change the data."""

    def test_import_existing_url(self, db_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(db_with_url)
        with log_stats(self), block_downloads():
            self.plugin_class(db_with_url, url=self.url).import_url(self.url)

        validator = self.existing_url_validator()
        self.validate_plugin(db_with_url, original_plugin, validator)


class UpdateShowTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating a show restores randomized data."""

    def test_update_show(self, db_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(db_with_url)
        results = self._import_url(db_with_url)
        entity = self.get_random_show(results)
        self._update_and_validate(db_with_url, original_plugin, entity)


class UpdateSeasonTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating a season restores randomized data."""

    def test_update_season(self, db_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(db_with_url)
        results = self._import_url(db_with_url)
        entity = self.get_random_season(results)
        self._update_and_validate(db_with_url, original_plugin, entity)


class UpdateEpisodeTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating an episode restores randomized data."""

    def test_update_episode(self, db_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(db_with_url)
        results = self._import_url(db_with_url)
        entity = self.get_random_episode(results)
        self._update_and_validate(db_with_url, original_plugin, entity)
        # assert False


class DeletedEpisodeTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that a fake episode gets soft-deleted during update_season."""

    def test_deleted_episode(self, db_with_url: Session) -> None:
        results = self._import_url(db_with_url)
        season = self.get_random_season(results)

        fake_episode = build_random_model(
            Episode,
            season_id=season.id,
            deleted_at=None,
        )
        season.episodes.append(fake_episode)
        db_with_url.flush()

        fake_episode.soft_delete()
        original_plugin = self.get_detached_plugin(db_with_url)
        fake_episode.soft_undelete()

        with mock_update(self.files_directory_path()), log_stats(self):
            self.plugin_class(db_with_url, season=season).update_season(season)
            db_with_url.flush()

        self.validate_plugin(
            db_with_url,
            original_plugin,
            self.deleted_episode_validator(fake_episode),
        )


class DeletedSeasonTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that a fake season gets soft-deleted during update_show."""

    def test_deleted_season(self, db_with_url: Session) -> None:
        results = self._import_url(db_with_url)
        show = self.get_random_show(results)

        fake_season = build_random_model(
            Season,
            show_id=show.id,
            deleted_at=None,
        )
        show.seasons.append(fake_season)
        db_with_url.flush()

        fake_season.soft_delete()
        original_plugin = self.get_detached_plugin(db_with_url)
        fake_season.soft_undelete()

        with mock_update(self.files_directory_path()), log_stats(self):
            self.plugin_class(db_with_url, show=show).update_show(show=show)
            db_with_url.flush()

        self.validate_plugin(
            db_with_url,
            original_plugin,
            self.deleted_season_validator(fake_season),
        )


class SearchTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that searching returns results."""

    def test_search(self, db_with_files: Session) -> None:
        if not self.search_query:
            pytest.skip()

        result = self._search(db_with_files, self.search_query)

        assert isinstance(result, PluginSearchResults)
        assert len(result.results) > 0


class AllUpdatesTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Exhaustive test that updates every entity individually."""

    @pytest.mark.skip(reason="Exhaustive test - run manually")
    def test_all_updates(self, db_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(db_with_url)
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


# endregion Individual Test Mixins

# region Grouped Mixins


class URLTests[PluginT: BasePlugin](
    ParseURLTests[PluginT],
    ParseURLVariantTests[PluginT],
    ImportURLTests[PluginT],
    ImportExistingURLTests[PluginT],
):
    """All URL-related tests: parsing, importing, and re-importing."""


class UpdateTests[PluginT: BasePlugin](
    UpdateShowTests[PluginT],
    UpdateSeasonTests[PluginT],
    UpdateEpisodeTests[PluginT],
):
    """All entity update tests."""


class DeletionTests[PluginT: BasePlugin](
    DeletedEpisodeTests[PluginT],
    DeletedSeasonTests[PluginT],
):
    """All soft-deletion tests."""


class StandardTests[PluginT: BasePlugin](
    URLTests[PluginT],
    UpdateTests[PluginT],
    DeletionTests[PluginT],
    AllUpdatesTests[PluginT],
):
    """The standard set of tests for a plugin with URL import support."""


class InvalidURLValidator[PluginT: BasePlugin](
    InvalidImportURLTests[PluginT],
    PluginValidator[PluginT],
):
    """Validator for plugins with invalid URLs that should raise errors."""

    invalid_url = True


# endregion Grouped Mixins
