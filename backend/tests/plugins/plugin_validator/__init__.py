# TODO: Validate
import json
import os
import random
from collections.abc import Callable
from contextlib import nullcontext
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
    PluginSearchResults,
    URLImportResult,
)
from plugins.utils.base_plugin import BasePlugin
from tests.app.utils.utils import build_random_model
from tests.plugins.plugin_validator.database import DatabaseMixin
from tests.plugins.plugin_validator.log_stats import log_stats
from tests.plugins.plugin_validator.mocks import (
    block_downloads,
    mock_update,
    track_downloads,
)
from tests.plugins.plugin_validator.validator import Validator


class PluginValidator[PluginT: BasePlugin](DatabaseMixin[PluginT]):
    """Base class with shared configuration, validation helpers, and data initialization."""

    plugin_class: type[PluginT]
    url: str | None = None
    search_url: str | None = None
    parse_url_response: object | None = None
    url_path_patterns: tuple[str, ...] = ()
    invalid_url = False
    search_query: str | None = None

    def get_detached_plugin(self, session: Session) -> Plugin:
        """Return a detached copy of the plugin to use for validation."""
        plugin = self.select_plugin_with_children(session)
        dumped = self._dump_model(plugin)
        return self._load_model(Plugin, dumped)

    def validate_plugin(
        self,
        session: Session,
        original_plugin: Plugin,
        config: Validator,
    ) -> None:
        """Validate that the current database state matches the original plugin."""
        config.validate(original_plugin, self.get_detached_plugin(session))

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

    def update_plugin_validator(self, session: Session, plugin: Plugin) -> Validator:  # noqa: ARG002
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
        entity: Source | Show | Season | Episode,
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

    def _get_update_function(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Callable[[], None]:
        """Return the appropriate plugin update function for the entity type."""
        match entity:
            case Plugin() as plugin:
                return lambda: self.plugin_class(session).update_plugin(plugin=plugin)
            case Source() as source:
                return lambda: self.plugin_class(session).update_source(
                    source=source,
                )
            case Show() as show:
                return lambda: self.plugin_class(session).update_show(show=show)
            case Season() as season:
                return lambda: self.plugin_class(session).update_season(
                    season,
                )
            case Episode() as episode:
                return lambda: self.plugin_class(session).update_episode(
                    episode,
                )

    def _get_validator(
        self,
        session: Session,
        entity: Plugin | Source | Show | Season | Episode,
    ) -> Validator:
        """Return the default validator for the given entity type."""
        match entity:
            case Plugin() as plugin:
                return self.update_plugin_validator(session, plugin)
            case Source() as source:
                return self.update_source_validator(source)
            case Show() as show:
                return self.update_show_validator(show)
            case Season() as season:
                return self.update_season_validator(season)
            case Episode() as episode:
                return self.update_episode_validator(episode)

    def _update_and_validate(
        self,
        session: Session,
        original_plugin: Plugin,
        entity: Plugin | Source | Show | Season | Episode,
        validator: Validator | None = None,
        *,
        use_mock_update: bool = True,
    ) -> None:
        """Mark an entity as outdated, run its update, and validate the result."""
        assert entity.data_timestamp
        entity.update_at = entity.data_timestamp + timedelta(seconds=1)
        if isinstance(entity, (Show, Season, Episode)):
            entity.extra = "Outdated"
        validator = validator or self._get_validator(session, entity)
        update = self._get_update_function(session, entity)

        maybe_mock_wrapper = mock_update() if use_mock_update else nullcontext()
        with maybe_mock_wrapper, log_stats(self):
            update()
            session.flush()

        msg = f"Failed updating: {entity}"
        try:
            self.validate_plugin(session, original_plugin, validator)
        except AssertionError as error:
            raise AssertionError(msg) from error

    def _initialize_import_data(
        self,
        session: Session,
        *,
        files_already_cached: bool,
    ) -> None:
        """Import URL data, always exporting files for analysis even on failure."""
        try:
            with track_downloads() as download_count:
                if self.invalid_url:
                    with pytest.raises(InvalidURLError):
                        self._import_url(session)
                else:
                    self._import_url(session)
        finally:
            self._export_database_files(session)

        if not self.invalid_url:
            self._export_verification_file(session)

        if files_already_cached and download_count:
            pytest.fail(f"Files were downloaded during import: {download_count}")

    def _initialize_search_data(
        self,
        session: Session,
        search_query: str,
        *,
        files_already_cached: bool,
    ) -> None:
        """Run a search query, always exporting files for analysis even on failure."""
        # Search results auto-refresh after a plugin TTL (e.g. 30 days). When
        # replaying cached data, freeze the clock to just after the search file
        # was recorded so the TTL treats it as fresh instead of re-downloading.
        freeze_target = None
        if files_already_cached:
            plugin = self.select_plugin_with_children(session)
            search_timestamps = [
                file.data_timestamp
                for file in plugin.files
                if file.key.startswith("Search")
            ]
            if search_timestamps:
                freeze_target = max(search_timestamps) + timedelta(seconds=1)

        try:
            with freeze_time(freeze_target), track_downloads() as download_count:
                self._search(session, search_query)
        finally:
            self._export_database_files(session)

        if files_already_cached and download_count:
            pytest.fail(f"Files were downloaded during search: {download_count}")

    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Records/refreshes test data locally; never runs on CI.",
    )
    def test__initialize_test_data(
        self,
        session_with_files: Session,
    ) -> None:
        """Downloads and saves all of the data required for the tests.

        On first run this will download files and export them. Subsequent runs
        verify that all files are served from cache (no downloads occur).
        """
        pytest.skip("TEMP: JUST IN CASE")
        files_already_cached = self.combined_files_path().exists()

        if self.url:
            self._initialize_import_data(
                session_with_files,
                files_already_cached=files_already_cached,
            )

        if self.search_query:
            self._initialize_search_data(
                session_with_files,
                self.search_query,
                files_already_cached=files_already_cached,
            )


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

    def test_import_url(self, session_with_files: Session) -> None:
        if not self.url or self.invalid_url:
            pytest.skip()

        with block_downloads(), log_stats(self):
            self.plugin_class(session_with_files).import_url(self.url)

        verification_content = self.verification_file_path().read_text()
        verification_data = json.loads(verification_content)

        original_plugin = self._load_model(Plugin, verification_data)
        validator = self.import_url_validator()
        self.validate_plugin(session_with_files, original_plugin, validator)


class InvalidImportURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that importing an invalid URL raises InvalidURLError."""

    def test_import_url(self, session_with_files: Session) -> None:
        if not self.url:
            pytest.skip()

        with block_downloads(), log_stats(self), pytest.raises(InvalidURLError):
            self.plugin_class(session_with_files).import_url(self.url)


class ImportExistingURLTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that re-importing an existing URL doesn't change the data."""

    def test_import_existing_url(self, session_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(session_with_url)
        with log_stats(self), block_downloads():
            self.plugin_class(session_with_url).import_url(self.url)

        validator = self.existing_url_validator()
        self.validate_plugin(session_with_url, original_plugin, validator)


class UpdateShowTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating a show restores randomized data."""

    def test_update_show(self, session_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(session_with_url)
        results = self._import_url(session_with_url)
        entity = self.get_random_show(results)
        self._update_and_validate(session_with_url, original_plugin, entity)


class UpdateSeasonTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating a season restores randomized data."""

    def test_update_season(self, session_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(session_with_url)
        results = self._import_url(session_with_url)
        entity = self.get_random_season(results)
        self._update_and_validate(session_with_url, original_plugin, entity)


class UpdateEpisodeTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating an episode restores randomized data."""

    def test_update_episode(self, session_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(session_with_url)
        results = self._import_url(session_with_url)
        entity = self.get_random_episode(results)
        self._update_and_validate(session_with_url, original_plugin, entity)
        # assert False


class UpdateSourceTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that updating a source propagates upstream changes."""

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

    def test_update_source(self, session_with_url: Session) -> None:
        """Update a random source and validate the data."""
        if self.invalid_url or not self.url:
            pytest.skip()

        plugin_instance = self.plugin_class(session_with_url)
        results = plugin_instance.import_url(self.url)
        source = self.get_random_source(results)

        timestamp = tz_datetime.now() + timedelta(minutes=1)
        self._create_source_update_entry(plugin_instance, source, timestamp)

        # Seed update_at later than the pending release_date so set_update_at
        # overwrites it with the earlier value — gives the validator a
        # decrementing write to assert.
        source.shows[0].update_at = timestamp + timedelta(minutes=1)
        for season in source.shows[0].seasons:
            if season.update_at:
                season.update_at = timestamp + timedelta(minutes=1)

        original_plugin = self.get_detached_plugin(session_with_url)
        self._update_and_validate(session_with_url, original_plugin, source)


class DeletedEpisodeTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that a fake episode gets soft-deleted during update_season."""

    def test_deleted_episode(self, session_with_url: Session) -> None:
        results = self._import_url(session_with_url)
        season = self.get_random_season(results)
        assert season.data_timestamp

        freeze_at = season.data_timestamp + timedelta(seconds=1)

        with freeze_time(freeze_at):
            fake_episode = build_random_model(
                Episode,
                "full",
                season_id=season.id,
                deleted_at=tz_datetime.now(),
            )
        season.episodes.append(fake_episode)

        original_plugin = self.get_detached_plugin(session_with_url)
        fake_episode.soft_undelete()
        session_with_url.flush()

        freeze_at = season.data_timestamp + timedelta(seconds=2)
        with freeze_time(freeze_at), block_downloads(), log_stats(self):
            self.plugin_class(session_with_url).update_season(season=season)

        validator = self.deleted_episode_validator(fake_episode)
        self.validate_plugin(session_with_url, original_plugin, validator)


class DeletedSeasonTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that a fake season gets soft-deleted during update_show."""

    def test_deleted_season(self, session_with_url: Session) -> None:
        results = self._import_url(session_with_url)
        show = self.get_random_show(results)
        assert show.data_timestamp

        freeze_at = show.data_timestamp + timedelta(seconds=1)

        with freeze_time(freeze_at):
            fake_season = build_random_model(
                Season,
                "full",
                show_id=show.id,
                deleted_at=tz_datetime.now(),
            )
        show.seasons.append(fake_season)

        original_plugin = self.get_detached_plugin(session_with_url)
        fake_season.soft_undelete()
        session_with_url.flush()

        freeze_at = show.data_timestamp + timedelta(seconds=2)
        with freeze_time(freeze_at), block_downloads(), log_stats(self):
            self.plugin_class(session_with_url).update_show(show=show)

        validator = self.deleted_season_validator(fake_season)
        self.validate_plugin(session_with_url, original_plugin, validator)


class SearchTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Tests that searching returns results."""

    def test_search(self, session_with_files: Session) -> None:
        if not self.search_query:
            pytest.skip()

        with block_downloads(), log_stats(self):
            result = self._search(session_with_files, self.search_query)

        assert isinstance(result, PluginSearchResults)
        assert len(result.results) > 0

        url = self.search_url or self.url
        assert url

        stripped_url = (
            url.removeprefix("https://")
            .removeprefix("http://")
            .removeprefix("www.")
            .removesuffix("/")
        )
        assert any(
            stripped_url in search_result.url for search_result in result.results
        )


class AllUpdatesTests[PluginT: BasePlugin](PluginValidator[PluginT]):
    """Exhaustive test that updates every entity individually."""

    @pytest.mark.skip(reason="Exhaustive test - run manually")
    def test_all_updates(self, session_with_url: Session) -> None:
        original_plugin = self.get_detached_plugin(session_with_url)
        plugin = self.select_plugin_with_children(session_with_url)

        for source in plugin.sources:
            for show in source.shows:
                if show.data_timestamp:
                    self._update_and_validate(session_with_url, original_plugin, show)
                    session_with_url.rollback()
                for season in show.seasons:
                    self._update_and_validate(session_with_url, original_plugin, season)
                    session_with_url.rollback()
                    for episode in season.episodes:
                        self._update_and_validate(
                            session_with_url,
                            original_plugin,
                            episode,
                        )
                        session_with_url.rollback()


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
    SearchTests[PluginT],
    AllUpdatesTests[PluginT],
):
    """The standard set of tests for a plugin with URL import support."""


class InvalidURLValidator[PluginT: BasePlugin](
    InvalidImportURLTests[PluginT],
    PluginValidator[PluginT],
):
    """Validator for plugins with invalid URLs that should raise errors."""

    invalid_url = True
