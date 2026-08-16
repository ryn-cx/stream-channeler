# TODO: Validate
"""The plugin's own source, kept up to date from HiDive's release schedule."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import override

from diving_board.schedule.group_list import models as group_list_models
from loguru import logger

from app.sources.models import Source
from plugins.HiDive.files import (
    Schedule,
    diving_board,
)
from plugins.HiDive.helpers import HelperMixin
from plugins.utils.base_plugin.files import COMPLETED_STATUS, EXTRA_STATUS_FIELD

# TODO: Add support for individual episodes of a series.

# What separates a card's show name from the episode title it is written with.
_SHOW_NAME_SEPARATOR = " - "


# TODO: Validate
def _element_text(element: group_list_models.Element) -> str:
    """Return the text a card's element is written with."""
    if not element.attributes.text:
        msg = "Schedule card element has no text."
        raise ValueError(msg)
    return element.attributes.text


# TODO: Validate
class SourceMixin(HelperMixin, register=False):
    """Reading the schedule for what the source's titles are about to gain."""

    # TODO: Validate
    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_schedule_file = self.schedule_file(source.data_timestamp)
        new_schedule_file.download_if_outdated(source.update_at)
        self._process_new_schedule_files(source)
        self._upsert_source()

    # TODO: Validate
    def _process_new_schedule_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()
        # TODO: Is there a better way to lookup shows?
        shows_by_name = {show.name: show for show in source.shows if show.name}

        for schedule_file in self.get_incomplete_files(Schedule, self.schedule_file):
            logger.info(
                "Processing schedule file: {}",
                schedule_file.database_record.key,
            )
            for page in schedule_file.parsed():
                group_list = diving_board().schedule.extract_group_list(page)
                for group in group_list.attributes.groups:
                    for card in group.attributes.cards:
                        # Layout: content[0].elements[0] is the ISO release date,
                        # elements[1] is "Show Name - Episode Title".
                        elements = card.attributes.content[0].attributes.elements
                        release_date = datetime.fromisoformat(
                            _element_text(elements[0]),
                        ).astimezone()
                        show_name = _element_text(elements[1]).split(
                            _SHOW_NAME_SEPARATOR,
                            1,
                        )[0]
                        if show := shows_by_name.get(show_name):
                            show.set_update_at(release_date)
                            for season in show.seasons:
                                season.set_update_at(release_date)

            schedule_file.database_record.extra = {
                EXTRA_STATUS_FIELD: COMPLETED_STATUS,
            }

    # TODO: Validate
    def _upsert_source(self) -> Source:
        if not (latest_schedule_file := self.get_latest_schedule_file()):
            latest_schedule_file = self._initial_file(Schedule)
            latest_schedule_file.download_if_outdated()
        data_timestamp = latest_schedule_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())
