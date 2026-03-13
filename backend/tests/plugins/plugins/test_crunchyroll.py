from datetime import timedelta
from typing import override

import pytest
from chirashi.browse_series import BrowseSeries
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.plugins.Crunchyroll import Crunchyroll
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from tests.plugins.plugin_validator import InvalidURLValidator, PluginValidator
from tests.plugins.plugin_validator.validator import Validator


class CrunchyrollValidator(PluginValidator):
    url: str
    show_key: str
    show_slug: str

    plugin_class = Crunchyroll

    @pytest.fixture(params=Crunchyroll.domains())
    def domain(self, request: pytest.FixtureRequest) -> str:
        return request.param

    @override
    def _update_show_validator(self, show: Show) -> Validator:
        validator = super()._update_show_validator(show)
        # Show shares a file with the seasons.
        validator.incremented(Season, "data_timestamp", "modified_at")

        return validator

    @override
    def _update_season_validator(self, season: Season) -> Validator:
        output = super()._update_season_validator(season)
        # Show shares a file with the seasons.
        output.incremented(Show, "data_timestamp", "modified_at")

        # All seasons share a file.
        output.incremented(Season, "data_timestamp", "modified_at")

        # Seasons share a file with the episode.
        for episode in season.episodes:
            output.incremented(episode.id, "data_timestamp", "modified_at")

        return output

    @override
    def _update_episode_validator(self, episode: Episode) -> Validator:
        output = super()._update_episode_validator(episode)
        # Seasons share a file with the episode.
        output.incremented(episode.season.id, "data_timestamp", "modified_at")

        # All episodes for a season share a file
        for sibling_episode in episode.season.episodes:
            output.incremented(sibling_episode.id, "data_timestamp", "modified_at")

        return output

    @pytest.fixture(
        params=[
            "/series/{key}/{slug}",
            "/series/{key}/",
            "/series/{key}",
        ],
    )
    def series_path(self, request: pytest.FixtureRequest) -> str:
        return request.param.format(key=self.show_key, slug=self.show_slug)

    def test_import_response(
        self,
        db_with_url: Session,
        domain: str,
        series_path: str,
    ) -> None:
        results = self._import_url(db_with_url, url=domain + series_path)
        result = results[0]

        assert len(results) == 1
        assert result.show.key == self.show_key
        assert result.whitelist_mode is False


class CrunchyrollSourceValidator(CrunchyrollValidator):
    @override
    def _update_source_validator(self, source: Source) -> Validator:
        validator = super()._update_source_validator(source)
        # The update at value is based on the timestamp of the Browse file and the test
        # will make a fake updated Browse file that will increment the update_at value.
        validator.incremented(Source, "update_at")

        # Show/Season will be modified when they are found in the Browse file.
        validator.incremented(Season, "modified_at")
        validator.incremented(Show, "modified_at")
        # update_at is populated/decremented because the release date is mocked to be a
        # sooner timestamp to test that the value is set correctly.
        validator.populated(Show, "update_at")
        for show in source.shows:
            for season in show.seasons[:-1]:
                validator.populated(season.id, "update_at")
            validator.decremented(show.seasons[-1].id, "update_at")

        return validator

    def test_update_source(self, db_with_url: Session) -> None:
        """Update a random source and validate the data."""
        if self.invalid_url or self.skip_update_tests or self.skip_test_update_source:
            pytest.skip()

        plugin_instance = self.plugin_class(db_with_url, url=self.url)
        results = plugin_instance.import_url(self.url)
        source = self._random_source(results)

        # Make a fake updated Browse file based on the existing one to simulate
        # downloading a new Browse file.
        assert isinstance(plugin_instance, Crunchyroll)
        existing_browse = plugin_instance._get_latest_browse_file()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_browse_timestamp = (
            existing_browse.database_entry.data_timestamp + timedelta(days=1)
        )
        # Directly editing the existing_browse file's parsed value is safe because these
        # changes will not be persisted to the database.
        for page in existing_browse.parsed():
            for entry in page.data:
                # Update all last_public values to make sure the value is newer than the
                # data_timestamp of the shows and seasons.
                entry.last_public = new_browse_timestamp
        new_browse = plugin_instance._browse_file(new_browse_timestamp)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_browse._write(BrowseSeries.dump_response(existing_browse.parsed()))  # pyright: ignore[reportPrivateUsage] # noqa: SLF001

        original_plugin = self._get_detached_plugin(db_with_url)
        self._update_and_validate(db_with_url, original_plugin, source)


class TestAiringSingleSeasonShow(CrunchyrollSourceValidator):
    show_key = "GT00365592"
    show_slug = "roll-over-and-die"
    url = f"crunchyroll.com/series/{show_key}/{show_slug}"


class TestAiringMultipleSeasonsShow(CrunchyrollSourceValidator):
    show_key = "G0XHWM17X"
    show_slug = "summer-pockets"
    url = f"crunchyroll.com/series/{show_key}/{show_slug}"


class InvalidCrunchyrollURLValidator(InvalidURLValidator):
    plugin_class = Crunchyroll


class TestInvalidSeriesKey(InvalidCrunchyrollURLValidator):
    url = "crunchyroll.com/series/ABCDEFGHI"


class TestInvalidPath(InvalidCrunchyrollURLValidator):
    url = "crunchyroll.com/watch/GT00365592"


class TestLargeShow(CrunchyrollValidator):
    show_key = "GRMG8ZQZR"
    show_slug = "one-piece"
    url = f"crunchyroll.com/series/{show_key}/{show_slug}"
