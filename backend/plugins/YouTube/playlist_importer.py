# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.titles.models import Title
from plugins.utils.base_plugin.media_type import MediaType
from plugins.YouTube.constants import LINKS_SOURCE_KEY
from plugins.YouTube.shared import (
    get_first_item,
    image_url,
    playlist_url,
    thumbnail_url,
)
from plugins.YouTube.user_importer import YouTubeUserImporter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class YouTubePlaylistImporter(YouTubeUserImporter):
    # TODO: Validate
    @property
    def links_source(self) -> Source:
        return self._sources[LINKS_SOURCE_KEY]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.playlist_info_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            self.playlist_items_file(season_key),
            self.playlist_info_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        playlist_item = get_first_item(
            self.playlist_info_file(title_key).parsed().items,
        )
        source = self.links_source

        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=playlist_item.snippet.title,
            description=playlist_item.snippet.description.replace("\x00", ""),
            url=playlist_url(title_key),
            media_type=MediaType.series,
            image_url=image_url(playlist_item.snippet.thumbnails),
            thumbnail_url=thumbnail_url(playlist_item.snippet.thumbnails),
            data_timestamp=data_timestamp,
            source_id=source.id,
            update_at=data_timestamp + timedelta(hours=6),
        ).upsert(source, existing_title)

        self._upsert_playlist_season(
            title=upserted_title,
            title_key=title_key,
            season_key=title_key,
            name=playlist_item.snippet.title,
            playlist=playlist_item,
        )
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return upserted_title
