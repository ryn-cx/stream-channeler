# TODO: Validate
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta

import pytest
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.plugins.Crunchyroll import Crunchyroll
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from tests.old_tests.plugins.helpers import get_urls
from tests.old_tests.plugins.plugin_validator import (
    Counter,
    PluginValidator,
    PluginValidatorBase,
    log_stats,
    # validator,
)
from tests.old_tests.plugins.validator import Validator

MockDownloadType = Callable[[], AbstractContextManager[None]]


@pytest.mark.parametrize(
    ("url"),
    get_urls(
        Crunchyroll.domains(),
        [
            # This series has a 9 character ID.
            "/series/GG5H5XQX4/frieren-beyond-journeys-end",
            "/series/GG5H5XQX4/",
            "/series/GG5H5XQX4",
            # This series has a 10 character ID.
            "/series/GT00365775/wash-it-all-away",
            "/series/GT00365775/",
            "/series/GT00365775",
        ],
    ),
)
def test_is_valid_url_format(url: str) -> None:
    assert Crunchyroll.is_valid_url_format(url)


@pytest.mark.parametrize(
    ("url"),
    [
        "crunchyroll.com/",
        "crunchyroll.com/series/",
        "crunchyroll.com/series/12345678",
        "crunchyroll.com/series/12345678/",
    ],
)
def test_is_invalid_url_format(url: str) -> None:
    assert not Crunchyroll.is_valid_url_format(url)


class CrunchyRollValidator(PluginValidator):
    plugin_class = Crunchyroll
    skip_test_set_season_update_at_using_episode_release_date = False

    # 1. Get plugin
    # 2. Check if show exists
    # 3. Preload Show files
    # 4. Preload Season files
    # 5. Preload Episode files
    # 6. Preload Browse files
    IMPORT_URL_QUERY_COUNT = 6

    # TODO: What are these queries?
    EXISTING_URL_QUERY_COUNT = 2

    # 1. Get plugin
    # 2. Check if show exists
    # 3. Preload Show files
    # 4. Preload Season files
    # 5. Preload Episode files
    # TODO: Why is this 2 queries?
    # 6-7. Preload Browse files
    UPDATE_SHOW_QUERY_COUNT = 7
    UPDATE_SEASON_QUERY_COUNT = 7
    UPDATE_EPISODE_QUERY_COUNT = 7

    # TODO: This is really sloppy
    # 1. Get plugin
    # 2. Preload Browse files
    # 3. TODO: ???
    # TODO: Why is this 2 queries?
    # 4-5. Get all shows
    # 6. Get all non-imported Browse files
    UPDATE_SOURCE_QUERY_COUNT = 7

    def _update_source_validator(self, source: Source) -> Validator:
        validator = super()._update_source_validator(source)
        for show in source.shows:
            # The show should be marked as outdated.
            validator.incremented(show.id, "modified_at")
            # Show.update_at uses changed because the initial value is None.
            validator.changed(show.id, "update_at")
            # There is no way to determine if the show was marked as outdated because it
            # has a new season or a new episode in a season so the seasons need to be
            # updated too.
            for season in show.seasons:
                validator.incremented(season.id, "modified_at")
                # Season.update_at uses changed because the initial value can be None.
                validator.changed(season.id, "update_at")

        return validator

    def _update_show_validator(self, show: Show) -> Validator:
        output = super()._update_show_validator(show)

        # All seasons share the show file so it will be updated
        output.incremented(Season, "modified_at")
        output.incremented(Season, "data_timestamp")
        return output

    def _update_season_validator(self, season: Season) -> Validator:
        output = super()._update_season_validator(season)

        # All seasons share the show file so it will be updated
        output.incremented(Season, "modified_at")
        output.incremented(Season, "data_timestamp")

        output.incremented(Show, "modified_at")
        output.incremented(Show, "data_timestamp")

        # Episode share a file with the season so their data will update.
        for episode in season.episodes:
            output.incremented(episode.id, "modified_at")
            output.incremented(episode.id, "data_timestamp")
        return output

    def _update_episode_validator(self, episode: Episode) -> Validator:
        output = super()._update_episode_validator(episode)

        # All the episodes for a season share single file so all episodes for the season
        # will update.
        for other_episode in episode.season.episodes:
            output.incremented(other_episode.id, "modified_at")
            output.incremented(other_episode.id, "data_timestamp")
        return output

    def test_import_response(self, db: Session) -> None:
        import_results = self._import_files_and_url(db)

        assert len(import_results) == 1
        import_result = import_results[0]
        assert import_result.show
        assert import_result.whitelist_mode is False

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
        with log_stats(self, sql_count):
            self.plugin_class(db, url=self.url).update_source(source)

        # Set data_timestamps back to the original value because update_source should
        # not modify this value.
        show.data_timestamp += timedelta(weeks=1)
        for season in show.seasons:
            season.data_timestamp += timedelta(weeks=1)

        self._validate_plugin(
            db,
            original_plugin,
            self._update_source_validator(source),
        )

    def test_set_season_update_at_using_episode_release_date(
        self,
        db: Session,
    ) -> None:
        """Import the URL, update the episode, and validate the data."""
        if self.skip_test_set_season_update_at_using_episode_release_date:
            pytest.skip("Skipped because skip_update_tests is True.")
        # Initialize plugin so files can be imported.
        results = self._import_files_and_url(db)
        show = self.select_show_with_parents(db, results[0].show)

        # The season order is basically random so the latest season needs to be found.
        max_season = show.seasons[0]
        for season in show.seasons[1:]:
            if season.sort_order > max_season.sort_order:
                max_season = season

        assert max_season.update_at


class TestSeriesWithMultipleSeasons(CrunchyRollValidator):
    # Must be a series with recently aired episodes to properly test update_source.
    url = "crunchyroll.com/series/GG5H5XQX4/frieren-beyond-journeys-end"


class TestSeriesWithSingleSeasons(CrunchyRollValidator):
    # Must be a series with recently aired episodes to properly test update_source.
    url = "crunchyroll.com/series/GT00365604/the-daily-life-of-a-part-time-torturer"


class TestSeriesWithNoEpisodes(CrunchyRollValidator):
    # This show is not airing so the source will not include the show.
    skip_test_update_source = True
    # There are no episodes so these cannot be used.
    skip_test_update_episode = True
    skip_test_set_season_update_at_using_episode_release_date = True
    # There are no seasons so this cannot be used.
    skip_test_update_season = True
    url = "crunchyroll.com/series/GRMEKVG8Y/claymore"


# Useful to test performance of functions
class TestLargeSeries(CrunchyRollValidator):
    skip_test_update_source = True
    skip_test_set_season_update_at_using_episode_release_date = True
    url = "crunchyroll.com/series/GRMG8ZQZR/one-piece"


class TestInvalidURL(PluginValidatorBase):
    plugin_class = Crunchyroll
    # Modified version of Claynmore's URL
    url = "crunchyroll.com/series/GRMEKVG8Z"

    def test_return_value(self, db: Session) -> None:
        with pytest.raises(
            InvalidURLError,
            match="Invalid Crunchyroll URL",
        ):
            self._import_files_and_url(db)

        self._export_all_files(db)
