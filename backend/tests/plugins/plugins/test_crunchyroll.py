# TODO: Validate
from datetime import datetime, timedelta

import pytest

try:
    from typing import override
except ImportError:
    from typing import override
from chirashi.browse_series import BrowseSeries
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.plugins.Crunchyroll import Crunchyroll
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator

# TODO: ADD TESTS FOR DELETIONS, CREATE FAKE SHOW/SEASON/EPISODE THEN MAKE SURE IT GETS
# DELETED WHEN UPDATE OCCURS.


class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    url_path_patterns = (
        "/series/{parse_url_response}/{show_slug}",
        "/series/{parse_url_response}/",
        "/series/{parse_url_response}",
    )

    @override
    def update_show_validator(self, show: Show) -> Validator:
        validator = super().update_show_validator(show)
        # update_at is recalculated by _set_update_at_from_episodes. Whether it
        # changes depends on episode release dates relative to data_timestamp.
        validator.ignore(show.id, "update_at")
        return validator

    @override
    def update_season_validator(self, season: Season) -> Validator:
        return (
            super()
            .update_season_validator(season)
            .episodes_share_season_file(season)
            .seasons_share_show_file(season)
        )

    @override
    def update_episode_validator(self, episode: Episode) -> Validator:
        return (
            super()
            .update_episode_validator(episode)
            .episodes_share_season_file(episode)
        )

    @override
    def deleted_season_validator(self, season: Season) -> Validator:
        validator = super().deleted_season_validator(season)
        # update_at is recalculated by _set_update_at_from_episodes.
        validator.ignore(season.show.id, "update_at")
        return validator


class CrunchyrollStandardTests(StandardTests[Crunchyroll], CrunchyrollValidator):
    pass


class CrunchyrollUpdateSourceTest(CrunchyrollValidator):
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # The update_at value is incremented because the fake browse file's
        # data_timestamp is set to now() on write, making update_at (timestamp + 1 day)
        # later than the original.
        validator = validator.incremented(Source, "update_at")

        # Show/Season will have a match which will set their update_at values.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # update_at is populated/decremented because the release date is mocked to be a
        # sooner timestamp to test that the value is set correctly.
        for show in source.shows:
            for season in show.seasons:
                if season.update_at is None:
                    validator = validator.populated(season.id, "update_at")
                else:
                    validator = validator.decremented(season.id, "update_at")

        return validator

    @staticmethod
    def _create_fake_browse_file(
        plugin_instance: Crunchyroll,
        timestamp: datetime,
        show_key: str,
    ) -> None:
        """Create a fake Browse file with updated last_public for the given show."""
        existing_browse = plugin_instance._get_latest_browse_file()  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        parsed = existing_browse.parsed()
        first_entry = parsed[0].data[0]
        assert first_entry is not None, "Browse file has no entries"
        first_entry.id = show_key
        first_entry.last_public = timestamp
        new_browse = plugin_instance._browse_file(timestamp)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_browse._write(BrowseSeries.dump_response(parsed))  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
        new_browse._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

    def test_update_source(self, session_with_url: Session) -> None:
        """Update a random source and validate the data."""
        if self.invalid_url:
            pytest.skip()

        if not self.url:
            msg = "URL is required for update source test"
            raise ValueError(msg)

        plugin_instance = self.plugin_class(session_with_url)
        results = plugin_instance.import_url(self.url)
        source = self.get_random_source(results)

        new_browse_timestamp = tz_datetime.now() + timedelta(minutes=1)
        self._create_fake_browse_file(
            plugin_instance,
            new_browse_timestamp,
            source.shows[0].key,
        )

        # Manually set show.update_at and season.update_at values so they will
        # always decrement.
        source.shows[0].update_at = new_browse_timestamp + timedelta(minutes=1)
        for season in source.shows[0].seasons:
            if season.update_at:
                season.update_at = new_browse_timestamp + timedelta(minutes=1)

        original_plugin = self.get_detached_plugin(session_with_url)
        self._update_and_validate(session_with_url, original_plugin, source)


class TestAiringSingleSeasonShow(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    # This needs to be a series with a recently aired episode.
    parse_url_response = "GT00374493"
    show_slug = "rilakkuma"
    url = f"crunchyroll.com/series/{parse_url_response}/{show_slug}"


class TestAiringMultipleSeasonsShow(
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTest,
):
    # This needs to be a series with a recently aired episode.
    parse_url_response = "G9VHN91DJ"
    show_slug = "the-angel-next-door-spoils-me-rotten"
    url = f"crunchyroll.com/series/{parse_url_response}/{show_slug}"


class InvalidCrunchyrollURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll


class TestInvalidSeriesKey(InvalidCrunchyrollURLValidator):
    url = "crunchyroll.com/series/GGGGGGGGG"


class TestInvalidURL(InvalidCrunchyrollURLValidator):
    url = "crunchyroll.com/watch/GT00365592"


class TestLargeShow(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    parse_url_response = "GRMG8ZQZR"
    show_slug = "one-piece"
    url = f"crunchyroll.com/series/{parse_url_response}/{show_slug}"
