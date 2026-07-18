from datetime import datetime
from typing import override

from chirashi.browse_series.models import BrowseSeriesModel

from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from plugins.Crunchyroll.files import chirashi
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.validator import Validator


class BaseCrunchyrollValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/series/{parse_url_response}/{show_slug}",
        "/series/{parse_url_response}/",
        "/series/{parse_url_response}",
    )


class CrunchyrollStandardTests(StandardTests[Crunchyroll], BaseCrunchyrollValidator):
    pass


class CrunchyrollUpdateSourceTest(
    UpdateSourceTests[Crunchyroll],
    BaseCrunchyrollValidator,
):
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # Source.update will mock download a new BrowseSeries file, this file will then
        # be used to set Source.data_timestamp, then Source.update_at will be set to 24
        # hours after Source.data_timestamp.
        # TODO: More accurate timestamp checking
        validator = validator.incremented(Source, "update_at")

        # Source.update will mock download a new BrowseSeries that includes a mock new
        # entry for the show. When a new entry for a show is added both the show and the
        # season will have their update_at value set.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # The existing seasons may or may not already have an update_at value.
        return validator.populated_or_decremented(Season, "update_at")

    def export_browse_file(
        self,
        plugin_instance: Crunchyroll,
        parsed: list[BrowseSeriesModel],
        timestamp: datetime,
    ) -> None:
        new_browse = plugin_instance.browse_file(timestamp)
        dumped = chirashi().browse_series.model_dump(parsed)
        new_browse.write(dumped)
        new_browse.database_record.data_timestamp = timestamp

    @override
    def _create_source_update_entry(
        self,
        plugin_instance: Crunchyroll,
        source: Source,
        timestamp: datetime,
    ) -> None:
        existing_browse = plugin_instance.get_latest_browse_file()
        parsed = existing_browse.parsed()
        first_entry = parsed[0].data[0]
        first_entry.id = source.shows[0].key
        first_entry.last_public = timestamp
        self.export_browse_file(plugin_instance, parsed, timestamp)


class TestAiringSingleSeasonShow(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    parse_url_response = "GQWH0MXPQ"
    show_slug = "anime-azurlane-slow-ahead"
    search_query = "Anime AzurLane: Slow Ahead!"
    search_url = "https://www.crunchyroll.com/series/GQWH0MXPQ"


class TestAiringMultipleSeasonsShow(
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTest,
):
    parse_url_response = "G9VHN91DJ"
    show_slug = "the-angel-next-door-spoils-me-rotten"
    search_query = "The Angel Next Door Spoils Me Rotten"
    search_url = "https://www.crunchyroll.com/series/G9VHN91DJ"


class TestCompletedSingleSeasonShow(
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTest,
):
    parse_url_response = "GEXH3W29Z"
    show_slug = "compass20-animation-project"
    search_query = "#COMPASS2.0 ANIMATION PROJECT"
    search_url = "https://www.crunchyroll.com/series/GEXH3W29Z"


class TestCompletedMultipleSeasonsShow(
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTest,
):
    parse_url_response = "GRVNZK5PY"
    show_slug = "a-certain-magical-index"
    search_query = "A Certain Magical Index"
    search_url = "https://www.crunchyroll.com/series/GRVNZK5PY"


class TestSingleEpisode(CrunchyrollStandardTests, CrunchyrollUpdateSourceTest):
    parse_url_response = "GT00375170"
    show_slug = "the-food-diary-of-miss-maid"
    episode_key = "GE00375439JAJP"
    episode_slug = "taiyaki-takoyaki-odango-convenience-store-onigiri-and-baumkuchen"
    urls = (
        "/watch/{episode_key}",
        "/watch/{episode_key}/",
        "/watch/{episode_key}/{episode_slug}",
    )


class InvalidCrunchyrollURLValidator(InvalidURLValidator[Crunchyroll]):
    plugin_class = Crunchyroll


class TestInvalidSeriesKey(InvalidCrunchyrollURLValidator):
    urls = ("crunchyroll.com/series/GGGGGGGGG",)


class TestInvalidWatchKey(InvalidCrunchyrollURLValidator):
    urls = ("crunchyroll.com/watch/GGGGGGGGGGGGGG",)
