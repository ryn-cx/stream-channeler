# TODO: Validate
from datetime import datetime
from typing import override

from diving_board.schedule.models import ScheduleModel

from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.HiDive import HiDive
from plugins.HiDive.files import diving_board
from tests.old_mess.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.old_mess.plugins.plugin_validator.validator import Validator


# TODO: Validate
class HiDiveValidator(PluginValidator[HiDive]):
    plugin_class = HiDive
    urls = (
        "/season/{parse_url_response}",
        "/season/{parse_url_response}/",
    )


# TODO: Validate
class HiDiveMovieValidator(PluginValidator[HiDive]):
    plugin_class = HiDive
    urls = (
        "/video/{parse_url_response}",
        "/video/{parse_url_response}/",
    )


# TODO: Validate
class HiDiveStandardTests(StandardTests[HiDive], HiDiveValidator):
    pass


# TODO: Validate
class HiDiveUpdateSourceTest(UpdateSourceTests[HiDive], HiDiveValidator):
    # TODO: Validate
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # Source.update will mock download a new Schedule file, this file will then
        # be used to set Source.data_timestamp, then Source.update_at will be set to 24
        # hours after Source.data_timestamp.
        validator = validator.incremented(Source, "update_at")

        # Source.update will mock download a new BrowseSeries that includes a mock new
        # entry for the show. When a new entry for a show is added both the show and the
        # season will have their update_at value set.
        validator = validator.incremented(Season, "modified_at")
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        # The existing seasons may or may not already have an update_at value.
        return validator.populated_or_decremented(Season, "update_at")

    # TODO: Validate
    @override
    def _create_source_update_entry(
        self,
        plugin_instance: HiDive,
        source: Source,
        timestamp: datetime,
    ) -> None:
        show_name = source.shows[0].name
        assert show_name is not None
        parsed = plugin_instance.get_latest_schedule_file().parsed()
        self._add_show_to_schedule(parsed, timestamp, show_name)
        self._export_schedule_file(plugin_instance, parsed, timestamp)

    # TODO: Validate
    def _add_show_to_schedule(
        self,
        parsed: list[ScheduleModel],
        timestamp: datetime,
        show_name: str,
    ) -> None:
        extract_group_list = diving_board().schedule.extract_group_list
        group_list = extract_group_list(parsed[0])
        elements = (
            group_list.attributes.groups[0]
            .attributes.cards[0]
            .attributes.content[0]
            .attributes.elements
        )
        elements[0].attributes.text = timestamp.replace(tzinfo=None).isoformat()
        elements[1].attributes.text = show_name

        page = parsed[0]
        for raw_index, raw_element in enumerate(page.elements):
            if raw_element.field_type == "groupList":
                page.elements[raw_index] = type(raw_element).model_validate(
                    group_list.model_dump(by_alias=True),
                )
                break

    # TODO: Validate
    def _export_schedule_file(
        self,
        plugin_instance: HiDive,
        parsed: list[ScheduleModel],
        timestamp: datetime,
    ) -> None:
        new_schedule = plugin_instance.schedule_file(timestamp)
        dumped = diving_board().schedule.model_dump(parsed)
        new_schedule.write(dumped)
        new_schedule.database_record.data_timestamp = timestamp


# TODO: Validate
class TestSingleSeasonShow(HiDiveStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "20022"
    search_query = "Tamako Market"
    search_url = "https://www.hidive.com/series/1286"


# TODO: Validate
class TestMultipleSeasonsShow(HiDiveStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "19427"
    search_query = "K-On"
    search_url = "https://www.hidive.com/series/1091"


# TODO: Validate
class TestMultipleSeasonsShowSecondSeasonURL(
    HiDiveStandardTests,
    HiDiveUpdateSourceTest,
):
    parse_url_response = "19425"
    search_query = "Non Non Biyori"
    search_url = "https://www.hidive.com/series/1189"


# TODO: Validate
class HiDiveMovieStandardTests(
    StandardTests[HiDive],
    HiDiveMovieValidator,
    HiDiveValidator,
):
    pass


# TODO: Validate
class TestMovie(HiDiveMovieStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "586784"
    search_query = "K-ON!: The Movie"


# TODO: Validate
class InvalidHiDiveURLValidator(InvalidURLValidator[HiDive]):
    plugin_class = HiDive


# TODO: Validate
class TestInvalidVideo(InvalidHiDiveURLValidator):
    parse_url_response = "1"
    urls = (f"hidive.com/video/{parse_url_response}",)


# TODO: Validate
class TestInvalidPlaylist(InvalidHiDiveURLValidator):
    parse_url_response = "1"
    urls = (f"hidive.com/playlist/{parse_url_response}",)


# TODO: Validate
class TestInvalidSeason(InvalidHiDiveURLValidator):
    parse_url_response = "1"
    urls = (f"hidive.com/season/{parse_url_response}",)
