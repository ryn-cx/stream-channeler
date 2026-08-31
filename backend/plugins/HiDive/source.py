# TODO: Validate
"""The plugin's own source, kept up to date from HiDive's release schedule."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import override

from diving_board.schedule import models as schedule_models
from loguru import logger
from sqlmodel import select

from app.channels.models import Channel
from app.channels.service import add_urls_to_channel_import_queue
from app.models import Visibility
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from plugins.HiDive.files import Schedule
from plugins.HiDive.utils import HelperMixin, schedule_group_list
from plugins.utils.base_plugin.files import COMPLETED_STATUS, EXTRA_STATUS_FIELD

# TODO: Add support for individual episodes of a series.


# TODO: Validate
def _element_text(element: schedule_models.Element2) -> str:
    """Return the text a card's element is written with."""
    text = element.attributes.text
    if not isinstance(text, str):
        msg = "Schedule card element has no text."
        raise TypeError(msg)
    return text


# TODO: Validate
def _element_release_date(element: schedule_models.Element2) -> datetime:
    """Return the day a card's element says the release is on."""
    text = element.attributes.text
    if not isinstance(text, datetime):
        msg = "Schedule card element has no release date."
        raise TypeError(msg)
    return text.astimezone()


# TODO: Validate
def _card_show_name(text: str) -> str:
    """Return the show a card is for, out of the "S1 E2 - Show Name" it is titled."""
    _episode_number, separator, show_name = text.partition(" - ")
    if not separator:
        msg = f"Schedule card title has no show name: {text}"
        raise ValueError(msg)
    return show_name


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
                        release_date = _element_release_date(elements[0])
                        show_name = _card_show_name(_element_text(elements[1]))
                        if show := shows_by_name.get(show_name):
                            show.set_update_at(release_date)
                            for season in show.seasons:
                                season.set_update_at(release_date)
                        else:
                            unmatched_names.append(show_name)

            self._queue_new_shows(unmatched_names)
            schedule_file.database_record.extra = {
                EXTRA_STATUS_FIELD: COMPLETED_STATUS,
            }

    # TODO: Validate
    def _queue_new_shows(self, show_names: list[str]) -> None:
        """Queue the titles a schedule file named that are not imported yet.

        A card names the show it is for but never the id of it, so the name is
        put back through HiDive's own search to be told which title it is.
        """
        new_show_urls: list[str] = []
        for show_name in dict.fromkeys(show_names):
            if show_url := self.search(show_name):
                logger.info("Queueing new title: {}", show_name)
                new_show_urls.append(show_url)
            else:
                logger.info("No search result for scheduled title: {}", show_name)

        # Queued in one call so the whole schedule file costs a single commit.
        if new_show_urls:
            add_urls_to_channel_import_queue(
                self.session,
                self._schedule_channel(),
                new_show_urls,
            )

    # TODO: Validate
    def _schedule_channel(self) -> Channel:
        """Return the plugin owned channel every HiDive title is queued into.

        HiDive's schedule only reaches forward, so a title drops off it once it
        has aired and the channel is what keeps hold of the whole run. It is
        created the first time a title is found rather than by hand.
        """
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == self.plugin_name()),
        ).first()
        if channel:
            return channel

        channel = Channel(
            name=self.plugin_name(),
            description=(Path(__file__).parent / "channel_description.md").read_text(
                encoding="utf-8",
            ),
            visibility=Visibility.public,
            anonymous=False,
            user_id=plugin_user.id,
        )
        self.session.add(channel)
        self.session.commit()
        return channel

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
            favicon_url=self.favicon_url(),
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())
