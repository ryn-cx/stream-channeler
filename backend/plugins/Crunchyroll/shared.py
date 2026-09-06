# TODO: Validate
"""What the plugin, its importers and its initializer all read Crunchyroll by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override
from urllib.parse import quote_plus

from sqlmodel import col, select

from app.canonical_media.filters import is_canonical
from app.sources.models import Source
from app.titles.models import Title, TitleCanonicalTitle
from plugins.Crunchyroll.base_files import CrunchyrollBaseFiles
from plugins.Crunchyroll.utils import MUSIC_SOURCE, VIDEO_SOURCE, build_url

if TYPE_CHECKING:
    from uuid import UUID


# TODO: Validate
class CrunchyrollShared(CrunchyrollBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str:
        return build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    def _available_canonical_title_ids(self) -> set[UUID]:
        linked_ids = select(TitleCanonicalTitle.canonical_title_id).join(
            Title,
            col(TitleCanonicalTitle.title_id) == col(Title.id),
        )
        own_ids = select(Title.id).where(is_canonical(Title))
        return {
            title_id
            for statement in (linked_ids, own_ids)
            for title_id in self.session.exec(
                statement.join(Source, col(Title.source_id) == col(Source.id)).where(
                    Source.plugin_id == self.plugin.id,
                    col(Title.deleted_at).is_(None),
                ),
            ).all()
        }
