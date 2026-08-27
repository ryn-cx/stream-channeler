# TODO: Validate
from datetime import datetime
from typing import override

from chirashi.browse_series.models import BrowseSeriesModel

from app.sources.models import Source
from plugins.Crunchyroll import Crunchyroll
from plugins.Crunchyroll.files import _chirashi
from tests.old_mess.plugins.crunchyroll.validators import (
    CrunchyrollStandardTests,
    CrunchyrollUpdateSourceTests,
    CrunchyrollValidator,
    crunchyroll_urls,
)


# TODO: Validate
class CrunchyrollVideoValidator(CrunchyrollValidator):
    urls = crunchyroll_urls("series/{parse_url_response}", "{show_slug}")


# TODO: Validate
class CrunchyrollVideoStandardTests(
    CrunchyrollStandardTests,
    CrunchyrollVideoValidator,
):
    pass


# TODO: Validate
class CrunchyrollVideoUpdateSourceTest(
    CrunchyrollUpdateSourceTests,
    CrunchyrollVideoValidator,
):
    # TODO: Validate
    def export_browse_file(
        self,
        plugin_instance: Crunchyroll,
        parsed: list[BrowseSeriesModel],
        timestamp: datetime,
    ) -> None:
        new_browse = plugin_instance.browse_series_file(timestamp)
        dumped = _chirashi().browse_series.model_dump(parsed)
        new_browse.write(dumped)
        new_browse.database_record.data_timestamp = timestamp

    # TODO: Validate
    @override
    def _create_source_update_entry(
        self,
        plugin_instance: Crunchyroll,
        source: Source,
        timestamp: datetime,
    ) -> None:
        existing_browse = plugin_instance.get_newest_browse_series_file()
        parsed = existing_browse.parsed()
        first_entry = parsed[0].data[0]
        first_entry.id = source.shows[0].key
        first_entry.last_public = timestamp
        self.export_browse_file(plugin_instance, parsed, timestamp)


# https://www.crunchyroll.com/series/GT00371926/please-excuse-my-younger-brothers


# TODO: Validate
class TestAiringSingleSeasonShow(
    CrunchyrollVideoStandardTests,
    CrunchyrollVideoUpdateSourceTest,
):
    parse_url_response = "GT00371926"
    show_slug = "please-excuse-my-younger-brothers"


# class TestAiringMultipleSeasonsShow(
#     CrunchyrollVideoStandardTests,
#     CrunchyrollVideoUpdateSourceTest,
# ):
#     parse_url_response = "GQWH0MXPQ"
#     show_slug = "anime-azurlane-slow-ahead"


# class TestCompletedSingleSeasonShow(
#     CrunchyrollVideoStandardTests,
#     CrunchyrollVideoUpdateSourceTest,
# ):
#     parse_url_response = "GEXH3W29Z"
#     show_slug = "compass20-animation-project"


# class TestCompletedMultipleSeasonsShow(
#     CrunchyrollVideoStandardTests,
#     CrunchyrollVideoUpdateSourceTest,
# ):
#     parse_url_response = "GRVNZK5PY"
#     show_slug = "a-certain-magical-index"


# class TestSingleEpisode(
#     CrunchyrollVideoStandardTests,
#     CrunchyrollVideoUpdateSourceTest,
# ):
#     parse_url_response = "GT00375170"
#     show_slug = "the-food-diary-of-miss-maid"
#     episode_key = "GE00375439JAJP"
#     episode_slug = "taiyaki-takoyaki-odango-convenience-store-onigiri-and-baumkuchen"
#     urls = crunchyroll_urls("watch/{episode_key}", "{episode_slug}")


# class TestMovie(CrunchyrollVideoStandardTests, CrunchyrollVideoUpdateSourceTest):
#     parse_url_response = "GMTE00335490"
#     show_slug = "spy-x-family-code-white"


# class TestMovieEpisode(CrunchyrollVideoStandardTests, CrunchyrollVideoUpdateSourceTest):
#     parse_url_response = "GMEE00380050JAJP"
#     show_slug = "x-the-movie"
#     episode_key = "GMEE00380050JAJP"
#     episode_slug = "x-the-movie"
#     urls = crunchyroll_urls("watch/{episode_key}", "{episode_slug}")


# class TestTMDBMismatch(CrunchyrollVideoStandardTests, CrunchyrollVideoUpdateSourceTest):
#     parse_url_response = "GG5H5XQX4"
#     show_slug = "frieren-beyond-journeys-end"


# class TestInvalidSeriesKey(InvalidCrunchyrollURLValidator):
#     urls = ("crunchyroll.com/series/GGGGGGGGG",)


# class TestInvalidWatchKey(InvalidCrunchyrollURLValidator):
#     urls = ("crunchyroll.com/watch/GGGGGGGGGGGGGG",)
