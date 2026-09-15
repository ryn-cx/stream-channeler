# TODO: Validate
"""What the plugin, its importers and its initializer all read HiDive by."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.media.media_type import TMDBMediaType
from app.sources.models import Source
from plugins.HiDive.base_files import HiDiveBaseFiles
from plugins.HiDive.files import Schedule
from plugins.HiDive.utils import (
    build_url,
    card_title_name,
    element_release_date,
    element_text,
    schedule_group_list,
)

if TYPE_CHECKING:
    from datetime import datetime

    from app.channels.models import Channel


# TODO: Validate
class HiDiveShared(HiDiveBaseFiles):
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
    @override
    def _next_source_update_at(self) -> datetime:
        return self._source_files_data_timestamp() + timedelta(days=1)

    # TODO: Validate
    def _process_new_schedule_files(self, source: Source) -> None:
        for schedule_file in self._incomplete_files(
            Schedule,
            self.schedule_file,
        ):
            # Queueing the titles a file found commits, which lets go of every
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the titles already imported.
            _cache = self._preload_sources(preload_seasons=True).all()
            # TODO: Is there a better way to lookup titles?
            titles_by_name = {
                title.name: title for title in source.titles if title.name
            }
            logger.info(
                "Processing schedule file: {}",
                schedule_file.record_key,
            )
            unmatched_names: list[str] = []
            for page in schedule_file.parsed():
                group_list = schedule_group_list(page)
                for group in group_list.attributes.groups or []:
                    for card in group.attributes.cards:
                        # Layout: content[0].elements[0] is the ISO release date,
                        # elements[1] is "S1 E2 - Title Name".
                        elements = card.attributes.content[0].attributes.elements
                        release_date = element_release_date(elements[0])
                        title_name = card_title_name(element_text(elements[1]))
                        if title := titles_by_name.get(title_name):
                            title.set_update_at(release_date)
                            for season in title.seasons:
                                season.set_update_at(release_date)
                        else:
                            unmatched_names.append(title_name)

            self._queue_new_titles(unmatched_names)
            schedule_file.clear_status()

    # TODO: Validate
    def search_for_title_url(
        self,
        name: str,
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.search_file(name)
        search_file.download_if_outdated()
        for element in search_file.parsed().elements:
            for card in element.attributes.cards or []:
                card_identifier = card.attributes.action.data.id
                type_prefix, _, title_key = card_identifier.partition("#")
                if type_prefix == "VOD":
                    return build_url(f"video/{title_key}")
                return build_url(f"series/{title_key}")
        return None

    # TODO: Validate
    def _queue_new_titles(self, title_names: list[str]) -> None:
        """Queue the titles a schedule file named that are not imported yet.

        A card gives the title's name but not its URL, so the name is matched
        against the imported catalogue to find it.
        """
        new_title_urls: list[str] = []
        for title_name in dict.fromkeys(title_names):
            if title_url := self.search_for_title_url(title_name, TMDBMediaType.tv):
                logger.info("Queueing new title: {}", title_name)
                new_title_urls.append(title_url)
            else:
                logger.info("No search result for scheduled title: {}", title_name)

        # Queued in one call so the whole schedule file costs a single commit.
        if new_title_urls:
            channel = self._schedule_channel()
            add_urls_to_channel_import_queue(self.session, channel, new_title_urls)

    # TODO: Validate
    def _schedule_channel(self) -> Channel:
        return self.get_or_create_channel(
            self.plugin_name(),
            self._channel_description("All Titles"),
        )
