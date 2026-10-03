# TODO: Validate
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, override

from diving_board.content_grid import (
    MOVIES_GRID_VIEW_CONFIG_ID,
    SERIES_GRID_VIEW_CONFIG_ID,
)
from loguru import logger

from plugins.HiDive.files import ContentGrid, Schedule, Search
from plugins.HiDive.movie_importer import HiDiveMovieImporter
from plugins.HiDive.series_importer import HiDiveSeriesImporter
from plugins.HiDive.shared import HiDiveShared
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from diving_board.content_grid import models as content_grid_models
    from diving_board.schedule import models as schedule_models
    from diving_board.search import models as search_models
    from diving_board.series import models as series_models
    from diving_board.vod import models as vod_models

    from app.files.models import File
    from app.sources.models import Source
    from app.titles.models import Title


# TODO: Validate
class HiDiveUpdater(HiDiveShared, BasePluginUpdater):
    # TODO: Validate
    def content_grid_file(self, grid_view_config_id: str) -> ContentGrid:
        return self._cached_file(ContentGrid, grid_view_config_id)

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        return self._cached_file(Search, query)

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        title_urls: list[str] = []
        for grid_view_config_id in (
            SERIES_GRID_VIEW_CONFIG_ID,
            MOVIES_GRID_VIEW_CONFIG_ID,
        ):
            grid_file = self.content_grid_file(grid_view_config_id)
            grid_file.download_if_outdated()
            for page in grid_file.parsed():
                card_list = self.single_element(page.elements, "cardList")
                title_urls.extend(
                    self._title_url_from_card(card)
                    # union-attr: This should raise an error if it fails.
                    for card in card_list.attributes.cards  # type: ignore[attr-defined, union-attr]
                )
        return title_urls

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        elements: Sequence[series_models.Element | vod_models.Element]
        if title.media_type == MediaType.movie:
            elements = self.vod_file(title.key).parsed().elements
        else:
            elements = self.series_file(title.key).parsed().elements
        return self.related_title_urls(elements)

    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        self._process_incomplete_schedule_files(self.source)

    def _process_incomplete_schedule_files(self, source: Source) -> None:
        for schedule_file in self._incomplete_files(
            Schedule,
            self.schedule_file,
        ):
            _cache = self._preload_sources(preload_seasons=True).all()
            titles_by_name = {title.name: title for title in source.titles}
            logger.info(
                "Processing schedule file: {}",
                schedule_file.record_key,
            )
            for page in schedule_file.parsed():
                group_list = self.single_element(page.elements, "groupList")
                # union-attr: This should raise an error if it fails.
                for group in group_list.attributes.groups:  # type: ignore[union-attr]
                    for card in group.attributes.cards:
                        # content[0].attributes.elements[0] is the ISO release date,
                        # content[0].attributes.elements[1] is "S1 E2 - Title Name".
                        elements = card.attributes.content[0].attributes.elements
                        release_date = elements[0].attributes.text
                        if not isinstance(release_date, datetime):
                            msg = "Schedule card element has no release date."
                            raise TypeError(msg)
                        release_date = release_date.astimezone()
                        title_name = self._extract_title(card)
                        if title := titles_by_name.get(title_name):
                            title.set_update_at(release_date)
                            for season in title.seasons:
                                season.set_update_at(release_date)
                        elif title_url := self._search_for_title_url(title_name):
                            self.add_new_urls_to_channel("All Titles", [title_url])
                        else:
                            msg = f"No search result for scheduled title: {title_name}"
                            raise ValueError(msg)

            schedule_file.clear_status()

    def _search_for_title_url(self, name: str) -> str | None:
        search_file = self.search_file(name)
        search_file.download_if_outdated()
        for element in search_file.parsed().elements:
            for card in element.attributes.cards or []:
                return self._title_url_from_card(card)
        return None

    @classmethod
    def _title_url_from_card(
        cls,
        card: content_grid_models.Card | search_models.Card,
    ) -> str:
        type_prefix, _, title_key = card.attributes.action.data.id.partition("#")
        if type_prefix == "VOD":
            return HiDiveMovieImporter.title_url(title_key)
        return HiDiveSeriesImporter.title_url(title_key)

    @classmethod
    def _extract_title(cls, card: schedule_models.Card) -> str:
        elements = card.attributes.content[0].attributes.elements
        text = elements[1].attributes.text
        if not isinstance(text, str):
            msg = "Schedule card element has no text."
            raise TypeError(msg)
        _, _, title_name = text.partition(" - ")
        if not title_name:
            msg = f"Schedule card title has no title name: {title_name}"
            raise ValueError(msg)
        return title_name

    # TODO: Validate
    def schedule_file(self, record: File | None = None) -> Schedule:
        if record is None:
            return self._cached_file(Schedule)
        return self._cached_file(
            Schedule,
            Schedule.file_to_unique_identifier(record),
        )

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[Schedule]:
        return [self.schedule_file()]
