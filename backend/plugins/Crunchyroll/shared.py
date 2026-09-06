# TODO: Validate
"""What the plugin, its importers and its initializer all read Crunchyroll by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override
from urllib.parse import quote_plus

from sqlmodel import col, select

from app.canonical_media.filters import is_canonical
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source
from plugins.Crunchyroll.basic_files import BasicFiles
from plugins.Crunchyroll.utils import MUSIC_SOURCE, VIDEO_SOURCE, build_url

if TYPE_CHECKING:
    from uuid import UUID


class CrunchyrollShared(BasicFiles):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    @classmethod
    def manual_search_url(cls, query: str) -> str:
        return build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    def _available_canonical_show_ids(self) -> set[UUID]:
        linked_ids = select(ShowCanonicalShow.canonical_show_id).join(
            Show,
            col(ShowCanonicalShow.show_id) == col(Show.id),
        )
        own_ids = select(Show.id).where(is_canonical(Show))
        return {
            show_id
            for statement in (linked_ids, own_ids)
            for show_id in self.session.exec(
                statement.join(Source, col(Show.source_id) == col(Source.id)).where(
                    Source.plugin_id == self.plugin.id,
                    col(Show.deleted_at).is_(None),
                ),
            ).all()
        }
