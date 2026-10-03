# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from sqlmodel import col, select

from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.utils.base_plugin.preload import BasePreloadMixin
from plugins.utils.base_plugin.upsert_files import BaseUpsertFilesMixin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class BaseRekeyMixin(BaseUpsertFilesMixin, BasePreloadMixin, ABC):
    # TODO: Validate
    def _canonical_title_key(self, title_key: str) -> str:
        return title_key

    # TODO: Validate
    def _superseded_titles(self, canonical_key: str, name: str | None) -> list[Title]:
        if not name:
            return []

        statement = (
            select(Title)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                Title.name == name,
                Title.key != canonical_key,
                col(Title.deleted_at).is_(None),
            )
        )
        superseded: list[Title] = []
        for candidate in self.session.exec(statement).unique():
            self._preload_and_download_title_files(candidate.key, tz_datetime.now())
            if self._canonical_title_key(candidate.key) == canonical_key:
                superseded.append(candidate)
        return superseded

    # TODO: Validate
    def _rekey_superseded_titles(
        self,
        superseded_titles: Sequence[Title],
        canonical_key: str,
    ) -> Sequence[Title]:
        canonical_titles = self._preload_title(
            canonical_key,
            preload_episodes=True,
        ).all()
        claimed_source_ids = {title.source_id for title in canonical_titles}
        for superseded_title in superseded_titles:
            if superseded_title.source_id in claimed_source_ids:
                superseded_title.soft_delete()
            else:
                superseded_title.key = canonical_key
        self.session.flush()
        return canonical_titles
