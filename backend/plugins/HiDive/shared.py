# TODO: Validate
"""What the plugin, its importers and its initializer all read HiDive by."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.media.media_type import TMDBMediaType
from app.sources.models import Source
from plugins.HiDive.basic_files import BasicFiles
from plugins.HiDive.files import Schedule
from plugins.HiDive.utils import (
    card_show_name,
    element_release_date,
    element_text,
    schedule_group_list,
    search_url,
)
from plugins.utils.base_plugin.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from app.channels.models import Channel

# https://www.hidive.com/series/1286
SERIES_URL_REGEX = r"\/series\/(?P<series_key>\d+)(?:\/|$)"
# https://www.hidive.com/season/20022
SEASON_URL_REGEX = r"\/season\/(?P<season_key>\d+)(?:\/|$)"
# https://www.hidive.com/video/586784
MOVIE_URL_REGEX = r"\/video\/(?P<movie_vod_key>\d+)(?:\/|$)"

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class HiDiveShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HIDIVE"

    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
            "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
        )

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        if not (latest_schedule_file := self.get_latest_schedule_file()):
            latest_schedule_file = self._initial_file(Schedule)
        data_timestamp = latest_schedule_file.data_timestamp()

        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(data_timestamp + timedelta(days=1))
        return source

    # TODO: Validate
    def _process_new_schedule_files(self, source: Source) -> None:
        for schedule_file in self.get_incomplete_files(Schedule, self.schedule_file):
            # Queueing the titles a file found commits, which lets go of every
            # show read for it, and a show nothing holds is not in memory to be
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the titles already imported.
            _cache = self._preload_sources(preload_seasons=True).all()
            # TODO: Is there a better way to lookup shows?
            shows_by_name = {show.name: show for show in source.shows if show.name}
            logger.info(
                "Processing schedule file: {}",
                schedule_file.database_record.key,
            )
            unmatched_names: list[str] = []
            for page in schedule_file.parsed():
                group_list = schedule_group_list(page)
                for group in group_list.attributes.groups or []:
                    for card in group.attributes.cards:
                        # Layout: content[0].elements[0] is the ISO release date,
                        # elements[1] is "S1 E2 - Show Name".
                        elements = card.attributes.content[0].attributes.elements
                        release_date = element_release_date(elements[0])
                        show_name = card_show_name(element_text(elements[1]))
                        if show := shows_by_name.get(show_name):
                            show.set_update_at(release_date)
                            for season in show.seasons:
                                season.set_update_at(release_date)
                        else:
                            unmatched_names.append(show_name)

            self._queue_new_shows(unmatched_names)
            schedule_file.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def _queue_new_shows(self, show_names: list[str]) -> None:
        """Queue the titles a schedule file named that are not imported yet.

        A card gives the show's name but not its URL, so the name is matched
        against the imported catalogue to find it.
        """
        new_show_urls: list[str] = []
        for show_name in dict.fromkeys(show_names):
            if show_url := self.search_for_url([show_name], TMDBMediaType.tv):
                logger.info("Queueing new title: {}", show_name)
                new_show_urls.append(show_url)
            else:
                logger.info("No search result for scheduled title: {}", show_name)

        # Queued in one call so the whole schedule file costs a single commit.
        if new_show_urls:
            channel = self._schedule_channel()
            add_urls_to_channel_import_queue(self.session, channel, new_show_urls)

    # TODO: Validate
    def _schedule_channel(self) -> Channel:
        """Return the plugin owned channel every HiDive title is queued into.

        HiDive's schedule only reaches forward, so a title drops off it once it
        has aired and the channel is what keeps hold of the whole run. It is
        created the first time a title is found rather than by hand.
        """
        return self.add_urls_to_plugin_channel(
            self.plugin_name(),
            (Path(__file__).parent / "channel_description.md").read_text(
                encoding="utf-8",
            ),
        )
