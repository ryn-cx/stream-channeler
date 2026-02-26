# TODO: Validate

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session

from app.media.models import Episode, Plugin, Season, Show, Source
from app.plugins.JustWatch import JustWatch
from app.plugins.utils.abstract_plugin import InvalidURLError
from app.plugins.utils.manage_plugins import import_plugins, plugins
from tests.plugins.helpers import get_domains
from tests.plugins.plugin_validator import Counter, PluginValidator, log_stats
from tests.plugins.validator import Validator

MockDownloadType = Callable[[], AbstractContextManager[None]]


def test_plugin_loads() -> None:
    import_plugins()
    assert JustWatch in plugins


@pytest.mark.parametrize(("url"), get_domains("justwatch.com"))
@pytest.mark.parametrize("prefix", ["", "SOURCE"])
@pytest.mark.parametrize(
    "path",
    ["/us/tv-show/fake-url", "/us/tv-show/fake-url/season-1"],
)
def test_is_valid_url_format(url: str, prefix: str, path: str) -> None:
    assert JustWatch.is_valid_url_format(prefix + url + path)


class JustWatchValidator(PluginValidator):
    plugin_class = JustWatch

    # 1. Get plugin
    # 2. Check if show exists
    EXISTING_URL_QUERY_COUNT = 2

    # 1. Get plugin
    # 2. Preload just the latest NewTitles
    # 3. Preload Source.shows
    # 4. Preload outdated NewTitles
    # 5. Preload all non-imported NewTitles
    # 6. Lookup matching season (this query could probably be combined with 3, but
    #    it's inconsistent usage in real world data make the performance difference
    #    negligible).
    UPDATE_SOURCE_QUERY_COUNT = 6


class JustWatchTVShowValidator(JustWatchValidator):
    # 1. Get plugin
    # 2. Check if show exists
    # 3. Preload UrlTitleDetails
    # 4. Preload CustomSeasonEpisodes
    # 5. Preload CustomBuyBoxOffers
    # 6. Preload NewTitles
    IMPORT_URL_QUERY_COUNT = 6

    # 1. Get plugin
    # 2. Get Sources/Shows/Season/Episode
    # 3. Preload UrlTitleDetails
    # 4. Preload CustomSeasonEpisodes
    # 5. Preload CustomBuyBoxOffers
    # 6. Preload NewTitles
    UPDATE_SHOW_QUERY_COUNT = 6
    UPDATE_SEASON_QUERY_COUNT = 6
    UPDATE_EPISODE_QUERY_COUNT = 6

    def _update_show_validator(self, show: Show) -> Validator:
        validator = super()._update_show_validator(show)
        # UrlTitleDetails is updated.
        validator.incremented(Show, "modified_at")
        validator.incremented(Show, "data_timestamp")

        # UrlTitleDetails is updated.
        validator.incremented(Season, "modified_at")
        validator.incremented(Season, "data_timestamp")

        return validator

    def _update_season_validator(self, season: Season) -> Validator:
        validator = super()._update_season_validator(season)
        # UrlTitleDetails is updated.
        validator.incremented(Show, "modified_at")
        validator.incremented(Show, "data_timestamp")

        # UrlTitleDetails and CustomSeasonEpisodes are updated.
        validator.incremented(Season, "modified_at")
        validator.incremented(Season, "data_timestamp")

        # CustomSeasonEpisodes is updated
        for episode in season.episodes:
            validator.incremented(episode.key, "modified_at")
            validator.incremented(episode.key, "data_timestamp")

        return validator

    def _update_episode_validator(self, episode: Episode) -> Validator:
        validator = super()._update_episode_validator(episode)

        # CustomSeasonEpisodes is updated
        for loop_episode in episode.season.episodes:
            validator.incremented(loop_episode.key, "modified_at")
            validator.incremented(loop_episode.key, "data_timestamp")

        return validator

    def _update_source_validator(self, source: Source) -> Validator:
        validator = super()._update_source_validator(source)
        show = source.shows[0]
        validator.changed(show.id, "update_at")  # From None to a date
        validator.incremented(show.id, "modified_at")

        return validator

    def test_update_source(
        self,
        db: Session,
        mock_download: MockDownloadType,
    ) -> None:
        """Import the URL, update the source, and make sure update_at is set."""
        if self.skip_update_tests:
            pytest.skip("Skipped because skip_update_tests is True.")
        if self.skip_test_update_source:
            pytest.skip("Skipped because skip_test_update_source is True.")

        results = self._import_files_and_url(db)
        show = self.select_show_with_parents(db, results[0].show)
        source = show.source

        # Set data_timestamps to make it appear like the existing data needs to be
        # updated.
        show.data_timestamp -= timedelta(weeks=1)
        for season in show.seasons:
            season.data_timestamp -= timedelta(weeks=1)

        for file in show.source.plugin.files:
            file.data_timestamp += timedelta(microseconds=1)
        db.commit()
        original_plugin = self._get_detached_plugin(db)

        sql_count = Counter()
        with (
            patch.object(self.plugin_class, "_download_missing_new_titles_files"),
            log_stats(self, sql_count),
        ):
            self.plugin_class(db, source=source).update_source(source)
        db.commit()

        self._validate_plugin(
            db,
            original_plugin,
            self._update_source_validator(source),
        )
        assert sql_count.value <= self.UPDATE_SOURCE_QUERY_COUNT


class JustWatchMovieValidator(JustWatchValidator):
    # 1. Get plugin
    # 2. Get Sources/Shows/Season/Episode
    # 3. Preload CustomBuyBoxOffers
    # 4. Preload NewTitles
    IMPORT_URL_QUERY_COUNT = 4

    # 1. Get plugin
    # 2. Get Sources/Shows/Season/Episode
    # 3. Preload UrlTitleDetails
    # 4. Preload NewTitles
    UPDATE_SHOW_QUERY_COUNT = 4
    UPDATE_SEASON_QUERY_COUNT = 4
    UPDATE_EPISODE_QUERY_COUNT = 4

    def _update_show_validator(self, show: Show) -> Validator:
        validator = super()._update_show_validator(show)
        # Source relies on the show file so it will be updated too
        validator.incremented_all("modified_at")
        validator.incremented_all("data_timestamp")
        validator.remove(Plugin, "modified_at", "data_timestamp")
        validator.remove(Source, "modified_at", "data_timestamp")
        return validator

    def _update_season_validator(self, season: Season) -> Validator:
        validator = super()._update_season_validator(season)
        # Source relies on the show file so it will be updated too
        validator.incremented_all("modified_at")
        validator.incremented_all("data_timestamp")
        validator.remove(Plugin, "modified_at", "data_timestamp")
        validator.remove(Source, "modified_at", "data_timestamp")
        return validator

    def _update_episode_validator(self, episode: Episode) -> Validator:
        validator = super()._update_episode_validator(episode)
        # Source relies on the show file so it will be updated too
        validator.incremented_all("modified_at")
        validator.incremented_all("data_timestamp")
        validator.remove(Plugin, "modified_at", "data_timestamp")
        validator.remove(Source, "modified_at", "data_timestamp")
        return validator

    def _update_source_validator(self, source: Source) -> Validator:
        validator = super()._update_source_validator(source)
        show = source.shows[0]
        for season in show.seasons:
            validator.incremented(season.id, "modified_at")
        validator.incremented(show.id, "modified_at")
        validator.changed(show.id, "update_at")

        return validator

    def test_update_source(
        self,
        db: Session,
        mock_download: MockDownloadType,
    ) -> None:
        """Import the URL, update the source, and make sure update_at is set."""
        if self.skip_update_tests:
            pytest.skip("Skipped because skip_update_tests is True.")
        if self.skip_test_update_source:
            pytest.skip("Skipped because skip_test_update_source is True.")

        results = self._import_files_and_url(db)
        original_plugin = self._get_detached_plugin(db)
        show = self.select_show_with_parents(db, results[0].show)
        source = show.source

        # Set data_timestamps to make it appear like the existing data needs to be
        # updated.
        show.data_timestamp -= timedelta(weeks=1)
        for season in show.seasons:
            season.data_timestamp -= timedelta(weeks=1)

        for file in show.source.plugin.files:
            file.data_timestamp += timedelta(microseconds=1)
        db.commit()

        sql_count = Counter()
        with (
            patch.object(self.plugin_class, "_download_missing_new_titles_files"),
            log_stats(self, sql_count),
        ):
            self.plugin_class(db, source=source).update_source(source)
        db.commit()

        # Set data_timestamps back to the original value because update_source should
        # not modify this value.
        show.data_timestamp += timedelta(weeks=1)
        for season in show.seasons:
            season.data_timestamp += timedelta(weeks=1)

        validator = self._update_source_validator(source)
        self._validate_plugin(db, original_plugin, validator)
        assert sql_count.value <= self.UPDATE_SOURCE_QUERY_COUNT


class TestInvalidMovieUrl(JustWatchMovieValidator):
    url = "justwatch.com/us/movie/invalid-url"
    skip_test_import_url = True
    skip_test_import_existing_url = True
    skip_update_tests = True
    skip_update_source = True

    def test_initialize_test_data(
        self,
        db: Session,
        disable_ip_validation: None,
    ) -> None:
        self._import_files(db)
        plugin_instance = self.plugin_class(db, url=self.url)
        with pytest.raises(InvalidURLError):
            plugin_instance.import_url(self.url)


class TestInvalidTVShowUrl(JustWatchMovieValidator):
    url = "justwatch.com/us/tv-show/invalid-url"
    skip_test_import_url = True
    skip_test_import_existing_url = True
    skip_update_tests = True
    skip_update_source = True

    def test_initialize_test_data(
        self,
        db: Session,
        disable_ip_validation: None,
    ) -> None:
        self._import_files(db)
        plugin_instance = self.plugin_class(db, url=self.url)
        with pytest.raises(InvalidURLError):
            plugin_instance.import_url(self.url)


class TestMovieNotAvailable(JustWatchMovieValidator):
    # 1. Get plugin
    # 2. Check if show exists
    # 3. Preload CustomBuyBoxOffers
    # 4. Preload NewTitles
    IMPORT_URL_QUERY_COUNT = 4
    EXISTING_URL_QUERY_COUNT = 4
    # When a movie is imported that is not available only the plugin will be in the
    # database because the show information needs to belong to a source.
    url = "justwatch.com/us/movie/code-geass-akito-the-exiled-5-to-beloved-ones"
    skip_update_tests = True
    skip_import_existing_url = True
    skip_update_source = True


class TestTVShowNotAvailable(JustWatchTVShowValidator):
    # 1. Get plugin
    # 2. Get Sources/Shows/Season/Episode
    # 3. Preload UrlTitleDetails
    # 4. Preload CustomSeasonEpisodes
    # 5. Preload CustomBuyBoxOffers
    # 6. Preload NewTitles
    EXISTING_URL_QUERY_COUNT = 6
    IMPORT_URL_QUERY_COUNT = 6
    # When a show is imported that is not available only the plugin will be in the
    # database because the show information needs to belong to a source.
    url = "justwatch.com/us/tv-show/darker-than-black"
    skip_update_tests = True
    skip_import_existing_url = True
    skip_update_source = True


class TestTVShowImportResponse(JustWatchTVShowValidator):
    url = "justwatch.com/us/tv-show/flcl"
    skip_update_tests = True
    skip_update_source = True

    def test_import_single_source(self, db: Session) -> None:
        url = "Adult Swimjustwatch.com/us/tv-show/flcl"
        results = self._import_files_and_url(db, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Adult Swim"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db: Session) -> None:
        url = "Adult Swim justwatch.com/us/tv-show/flcl"
        results = self._import_files_and_url(db, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Adult Swim"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_and_season(self, db: Session) -> None:
        url = "Adult Swimjustwatch.com/us/tv-show/flcl/season-1"
        results = self._import_files_and_url(db, url)
        assert len(results) == 1
        assert len(results[0].seasons) == 1
        assert isinstance(results[0].seasons[0], Season)
        assert not results[0].episodes

    def test_import_single_season(self, db: Session) -> None:
        url = "justwatch.com/us/tv-show/flcl/season-1"
        results = self._import_files_and_url(db, url)
        assert len(results) == 5  # noqa: PLR2004
        for result in results:
            assert len(result.seasons) == 1
            assert result.seasons[0].season_number == 1
            assert not result.episodes

    def test_import_everything(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        assert len(results) == 11  # noqa: PLR2004
        for result in results:
            assert not result.seasons
            assert not result.episodes


class TestMovieImportResponse(JustWatchMovieValidator):
    url = "justwatch.com/us/movie/scream-2022"
    skip_update_tests = True
    skip_update_source = True

    def test_import_single_source(self, db: Session) -> None:
        url = "Apple TVjustwatch.com/us/movie/scream-2022"
        results = self._import_files_and_url(db, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Apple TV Store"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_single_source_with_space(self, db: Session) -> None:
        url = "Apple TV justwatch.com/us/movie/scream-2022"
        results = self._import_files_and_url(db, url)
        assert len(results) == 1
        assert results[0].show.source.name == "Apple TV Store"
        assert not results[0].seasons
        assert not results[0].episodes

    def test_import_everything(self, db: Session) -> None:
        results = self._import_files_and_url(db)
        assert len(results) == 15  # noqa: PLR2004
        for result in results:
            assert not result.seasons
            assert not result.episodes


class TestTVShowWithMultipleSeasons(JustWatchTVShowValidator):
    # Must be a TV show with recently aired episodes to properly test update_source.
    skip_update_source = True
    url = "HBO Max https://www.justwatch.com/us/tv-show/schitts-creek"
    plugin_class = JustWatch


# TODO: Wait until one of these is available on the day it is added.
# class TestTVShowWithSingleSeasons(JustWatchTVShowValidator):
#     # Must be a TV show with recently aired episodes to properly test update_source.
#     skip_update_source = True
#     url = "Philo https://www.justwatch.com/us/tv-show/people-puzzler/season-1"
#     plugin_class = JustWatch


class TestMovie(JustWatchMovieValidator):
    plugin_class = JustWatch
    # This URL must be one that was very recently added to JustWatch.
    url = "Philo https://www.justwatch.com/us/movie/lust-for-gold"
