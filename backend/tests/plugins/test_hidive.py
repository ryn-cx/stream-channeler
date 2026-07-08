# TODO: Validate
from datetime import datetime
from typing import override

from diving_board.schedule.models import ScheduleModel

from app.shows.models import Show
from app.sources.models import Source
from plugins.HiDive import HiDive
from plugins.HiDive.files import diving_board
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
    UpdateSourceTests,
)
from tests.plugins.plugin_validator.validator import Validator


class HiDiveValidator(PluginValidator[HiDive]):
    plugin_class = HiDive
    urls = (
        "/season/{parse_url_response}",
        "/season/{parse_url_response}/",
    )


class HiDiveMovieValidator(PluginValidator[HiDive]):
    plugin_class = HiDive
    urls = (
        "/playlist/{parse_url_response}",
        "/playlist/{parse_url_response}/",
    )


class HiDiveStandardTests(StandardTests[HiDive], HiDiveValidator):
    pass


class HiDiveUpdateSourceTest(UpdateSourceTests[HiDive], HiDiveValidator):
    @override
    def update_source_validator(self, source: Source) -> Validator:
        validator = super().update_source_validator(source)
        # _upsert_source rewrites update_at = data_timestamp + 1 day off the
        # fresh fake schedule, so it's strictly later than the original.
        validator = validator.incremented(Source, "update_at")
        # The matched show and its seasons get their modified_at bumped when
        # set_update_at writes the release_date. The test seeds update_at to
        # a later value so the write decrements it.
        validator = validator.incremented(Show, "modified_at")
        validator = validator.decremented(Show, "update_at")
        for show in source.shows:
            for season in show.seasons:
                validator = validator.incremented(season.id, "modified_at")
                if season.update_at is None:
                    validator = validator.populated(season.id, "update_at")
                else:
                    validator = validator.decremented(season.id, "update_at")
        return validator

    @staticmethod
    def add_show_to_schedule(
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

    @staticmethod
    def export_schedule_file(
        plugin_instance: HiDive,
        parsed: list[ScheduleModel],
        timestamp: datetime,
    ) -> None:
        new_schedule = plugin_instance.schedule_file(timestamp)
        dumped = diving_board().schedule.dump(parsed)
        new_schedule.write(dumped)
        new_schedule._existing_database_record.data_timestamp = timestamp  # type: ignore[union-attr] # noqa: SLF001

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
        self.add_show_to_schedule(parsed, timestamp, show_name)
        self.export_schedule_file(plugin_instance, parsed, timestamp)


class TestSingleSeasonShow(HiDiveStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "20022"
    search_query = "Tamako Market"
    search_url = "https://www.hidive.com/series/1286"


class TestMultipleSeasonsShow(HiDiveStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "19427"
    search_query = "K-On"
    search_url = "https://www.hidive.com/series/1091"


class TestMultipleSeasonsShowSecondSeasonURL(
    HiDiveStandardTests,
    HiDiveUpdateSourceTest,
):
    parse_url_response = "19426"
    search_query = "K-On"
    search_url = "https://www.hidive.com/series/1091"


# https://www.hidive.com/season/19426


class HiDiveMovieStandardTests(
    StandardTests[HiDive],
    HiDiveMovieValidator,
    HiDiveValidator,
):
    pass


class TestMovie(HiDiveMovieStandardTests, HiDiveUpdateSourceTest):
    parse_url_response = "19919"
    search_query = "Tamako Market"


class InvalidHiDiveURLValidator(InvalidURLValidator[HiDive]):
    plugin_class = HiDive


class TestInvalidPlaylist(InvalidHiDiveURLValidator):
    parse_url_response = "1"
    urls = (f"hidive.com/playlist/{parse_url_response}",)


class TestInvalidSeason(InvalidHiDiveURLValidator):
    parse_url_response = "1"
    urls = (f"hidive.com/season/{parse_url_response}",)
