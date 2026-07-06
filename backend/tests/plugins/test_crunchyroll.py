# TODO: Validate
from datetime import datetime
from typing import override

from chirashi.browse_series import BrowseSeries

from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.validator import Validator

# TODO: ADD TESTS FOR DELETIONS, CREATE FAKE SHOW/SEASON/EPISODE THEN MAKE SURE IT GETS
# DELETED WHEN UPDATE OCCURS.


class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/series/{parse_url_response}/{show_slug}",
        "/series/{parse_url_response}/",
        "/series/{parse_url_response}",
    )


class CrunchyrollStandardTests(StandardTests[Crunchyroll], CrunchyrollValidator):
    pass


class CrunchyrollUpdateSourceTest(UpdateSourceTests[Crunchyroll], CrunchyrollValidator):
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
        existing_browse = plugin_instance.get_latest_browse_file()
        parsed = existing_browse.parsed()
        first_entry = parsed[0].data[0]
        assert first_entry is not None, "Browse file has no entries"
        first_entry.id = show_key
        first_entry.last_public = timestamp
        new_browse = plugin_instance.browse_file(timestamp)
        new_browse.write(BrowseSeries.dump_response(parsed))
        new_browse._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

    @override
    def _create_source_update_entry(
        self,
        plugin_instance: Crunchyroll,
        source: Source,
        timestamp: datetime,
    ) -> None:
        self._create_fake_browse_file(plugin_instance, timestamp, source.shows[0].key)


class TestAiringSingleSeasonShow(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    # This needs to be a series with a recently aired episode.
    parse_url_response = "GQWH0MXPQ"
    show_slug = "anime-azurlane-slow-ahead"

class TestAiringMultipleSeasonsShow(
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTest,
):
    # This needs to be a series with a recently aired episode.
    parse_url_response = "G9VHN91DJ"
    show_slug = "the-angel-next-door-spoils-me-rotten"


class InvalidCrunchyrollURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll


class TestInvalidSeriesKey(InvalidCrunchyrollURLValidator):
    urls = ("crunchyroll.com/series/GGGGGGGGG",)


class TestInvalidURL(InvalidCrunchyrollURLValidator):
    urls = ("crunchyroll.com/watch/GT00365592",)


class TestLargeShow(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    parse_url_response = "GRMG8ZQZR"
    show_slug = "one-piece"
