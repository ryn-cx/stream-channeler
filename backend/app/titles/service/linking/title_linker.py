# TODO: Validate

import re
import uuid
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, or_, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.service.linking import load_title_episodes, title_episodes
from app.episodes.service.names.vectors import TextMatcher
from app.media.media_type import TMDBMediaType
from app.plugins.identifiers import TMDB_SOURCE_KEY, TMDB_VIDEOS_SOURCE_KEY
from app.seasons.models import Season
from app.titles.models import Title
from app.titles.service.linking.episode_relinking import (
    _old_relink_episodes,
    _old_unlink_episodes_from_dropped_tmdb_titles,
    _relink_episode,
)
from app.titles.service.linking.tmdb_links import old_link_title_to_tmdb
from plugins.utils.manage_plugins import plugins

if TYPE_CHECKING:
    from collections.abc import Iterator

    from plugins.TMDB import TMDB
    from plugins.TMDB.updater import TMDBSearchResult
    from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
def _without_parentheses(name: str) -> str:
    return re.sub(r"\s*\([^()]*\)", "", name).strip()


# TODO: Validate
def _search_queries(name: str) -> list[str]:
    return [
        query for query in dict.fromkeys((name, _without_parentheses(name))) if query
    ]


# TODO: Validate
def _comparable_name(name: str) -> str:
    return re.sub(r"\W+", "", name.casefold())


# TODO: Validate
def _exact_name(name: str) -> str:
    return " ".join(name.casefold().split())


# TODO: Validate
def _is_exact_name(search_result: TMDBSearchResult, name: str) -> bool:
    names = {_exact_name(query) for query in _search_queries(name)}
    return any(_exact_name(result_name) in names for result_name in search_result.names)


# TODO: Validate
def _media_types_to_search(
    media_type: TMDBMediaType | None,
) -> list[TMDBMediaType | None]:
    if media_type is None:
        return [None]
    return [media_type, *(other for other in TMDBMediaType if other != media_type)]


# TODO: Validate
def _is_similar_name(search_result: TMDBSearchResult, name: str) -> bool:
    queries = {
        comparable
        for query in _search_queries(name)
        if (comparable := _comparable_name(query))
    }
    return any(
        (comparable_result := _comparable_name(result_name))
        and any(
            comparable_query in comparable_result
            or comparable_result in comparable_query
            for comparable_query in queries
        )
        for result_name in search_result.names
    )


# TODO: Validate
def _is_near_year(search_result: TMDBSearchResult, year: int | None) -> bool:
    if year is None:
        return True
    return any(abs(result_year - year) <= 5 for result_year in search_result.years)  # noqa: PLR2004


# TODO: Validate
class TitleLinker:
    # TODO: Validate
    def __init__(self, session: Session, title: Title) -> None:
        self.session = session
        self.title = title
        self.existing_links = {
            link.tmdb_title_id: link for link in title.tmdb_title_links
        }
        self.link_notes: dict[uuid.UUID, str | None] = {}
        self.new_links: dict[uuid.UUID, tuple[Title, str]] = {}
        self.matched_lookup_infos: set[TMDBLookupInfo] = set()

    # TODO: Validate
    def relink(self) -> None:
        if not self._is_linkable():
            return
        self._link_existing_links_of_validated_title()
        self._link_existing_manual_links()
        self._link_existing_links_with_hand_linked_episodes()
        self._link_exact_name_in_exact_year_search()
        self._link_exact_name_in_rough_year_search()
        self._link_exact_name_in_search_without_year()
        self._link_similar_name_near_year()
        self._save_links()

    # TODO: Validate
    def _is_linkable(self) -> bool:
        return (
            self.title.tmdb_absent_at is None
            and self.title.source.key != TMDB_VIDEOS_SOURCE_KEY
        )

    # TODO: Validate
    def _keep_existing_link(self, tmdb_title_id: uuid.UUID) -> None:
        if tmdb_title_id in self.existing_links:
            self.link_notes.setdefault(tmdb_title_id, None)

    # TODO: Validate
    def _link_tmdb_title(self, tmdb_title: Title, note: str) -> None:
        if tmdb_title.id in self.link_notes:
            return
        self.link_notes[tmdb_title.id] = note
        if tmdb_title.id not in self.existing_links:
            self.new_links[tmdb_title.id] = (tmdb_title, note)

    # TODO: Validate
    def _link_existing_links_of_validated_title(self) -> None:
        if self.title.tmdb_title_validated_at is None:
            return
        for tmdb_title_id in self.existing_links:
            self._keep_existing_link(tmdb_title_id)

    # TODO: Validate
    def _link_existing_manual_links(self) -> None:
        for tmdb_title_id, link in self.existing_links.items():
            if link.manual_tmdb_link:
                self._keep_existing_link(tmdb_title_id)

    # TODO: Validate
    def _link_existing_links_with_hand_linked_episodes(self) -> None:
        for tmdb_title_id in self._hand_linked_tmdb_title_ids():
            self._keep_existing_link(tmdb_title_id)

    # TODO: Validate
    def _link_exact_name_in_exact_year_search(self) -> None:
        for lookup_info in self._unmatched_lookup_infos():
            if lookup_info.year is None:
                continue
            self._link_exact_name(
                lookup_info,
                exact_year=lookup_info.year,
                rough_year=None,
                reason=f"Exact name in {lookup_info.year} search",
            )

    # TODO: Validate
    def _link_exact_name_in_rough_year_search(self) -> None:
        for lookup_info in self._unmatched_lookup_infos():
            if lookup_info.year is None:
                continue
            self._link_exact_name(
                lookup_info,
                exact_year=None,
                rough_year=lookup_info.year,
                reason=f"Exact name in search near {lookup_info.year}",
            )

    # TODO: Validate
    def _link_exact_name_in_search_without_year(self) -> None:
        for lookup_info in self._unmatched_lookup_infos():
            self._link_exact_name(
                lookup_info,
                exact_year=None,
                rough_year=None,
                reason="Exact name in search without a year",
            )

    # TODO: Validate
    def _link_exact_name(
        self,
        lookup_info: TMDBLookupInfo,
        exact_year: int | None,
        rough_year: int | None,
        reason: str,
    ) -> None:
        for search_results in self._searches(lookup_info, exact_year, rough_year):
            self._link_closest_description(
                lookup_info,
                [
                    search_result
                    for search_result in search_results
                    if _is_exact_name(search_result, lookup_info.name)
                    and _is_near_year(search_result, lookup_info.year)
                ],
                reason,
            )
            if lookup_info in self.matched_lookup_infos:
                return

    # TODO: Validate
    def _link_similar_name_near_year(self) -> None:
        for lookup_info in self._unmatched_lookup_infos():
            years = dict.fromkeys(
                [(lookup_info.year, None), (None, lookup_info.year), (None, None)],
            )
            note = (
                f"Automatic: Similar name near {lookup_info.year}"
                if lookup_info.year is not None
                else "Automatic: Similar name"
            )
            for exact_year, rough_year in years:
                for search_results in self._searches(
                    lookup_info,
                    exact_year,
                    rough_year,
                ):
                    self._link_first_importable(
                        lookup_info,
                        [
                            (search_result, note)
                            for search_result in search_results
                            if _is_similar_name(search_result, lookup_info.name)
                            and _is_near_year(search_result, lookup_info.year)
                        ],
                    )
                    if lookup_info in self.matched_lookup_infos:
                        break
                if lookup_info in self.matched_lookup_infos:
                    break

    # TODO: Validate
    def _link_closest_description(
        self,
        lookup_info: TMDBLookupInfo,
        search_results: list[TMDBSearchResult],
        reason: str,
    ) -> None:
        described_results = [
            (search_result, search_result.overview)
            for search_result in search_results
            if search_result.overview
        ]
        if (
            len(search_results) < 2  # noqa: PLR2004
            or not self.title.description
            or not described_results
        ):
            self._link_first_importable(
                lookup_info,
                [
                    (search_result, f"Automatic: {reason}")
                    for search_result in search_results
                ],
            )
            return

        scores = TextMatcher(
            [overview for _, overview in described_results],
        ).embedding_scores_of([self.title.description])[0]
        ranked_results = sorted(
            zip(
                [search_result for search_result, _ in described_results],
                scores,
                strict=True,
            ),
            key=lambda ranked_result: ranked_result[1],
            reverse=True,
        )
        self._link_first_importable(
            lookup_info,
            [
                (
                    search_result,
                    f"Automatic: {reason}, closest description ({round(score * 100)}%)",
                )
                for search_result, score in ranked_results
            ]
            + [
                (search_result, f"Automatic: {reason}")
                for search_result in search_results
                if not search_result.overview
            ],
        )

    # TODO: Validate
    def _link_first_importable(
        self,
        lookup_info: TMDBLookupInfo,
        noted_results: list[tuple[TMDBSearchResult, str]],
    ) -> None:
        for search_result, note in noted_results:
            import_results = self._tmdb.import_search_result(search_result)
            if not import_results:
                continue
            for import_result in import_results:
                self._link_tmdb_title(import_result.title, note)
            self.matched_lookup_infos.add(lookup_info)
            return

    # TODO: Validate
    def _searches(
        self,
        lookup_info: TMDBLookupInfo,
        exact_year: int | None,
        rough_year: int | None,
    ) -> Iterator[list[TMDBSearchResult]]:
        for media_type in _media_types_to_search(lookup_info.media_type):
            for query in _search_queries(lookup_info.name):
                yield self._tmdb.search(media_type, query, exact_year, rough_year)

    # TODO: Validate
    def _unmatched_lookup_infos(self) -> list[TMDBLookupInfo]:
        return [
            lookup_info
            for lookup_info in self._lookup_infos
            if lookup_info not in self.matched_lookup_infos
        ]

    # TODO: Validate
    @cached_property
    def _lookup_infos(self) -> list[TMDBLookupInfo]:
        plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
        plugin_key = self.title.source.plugin.key
        plugin_class = plugin_classes_by_key[plugin_key]
        plugin_instance = plugin_class(self.session, self.title.source.plugin)
        return list(dict.fromkeys(plugin_instance.tmdb_lookup_info(self.title)))

    # TODO: Validate
    @cached_property
    def _tmdb(self) -> TMDB:
        from plugins.TMDB import TMDB  # noqa: PLC0415

        return TMDB(self.session)

    # TODO: Validate
    def _save_links(self) -> None:
        title = self.title
        for tmdb_title_id, link in self.existing_links.items():
            if tmdb_title_id not in self.link_notes:
                self.session.delete(link)
            elif (note := self.link_notes[tmdb_title_id]) and link.note != note:
                link.note = note
                self.session.add(link)
        self.session.flush()
        self.session.expire(title, ["tmdb_title_links", "is_linked"])

        for tmdb_title, note in self.new_links.values():
            old_link_title_to_tmdb(self.session, title, tmdb_title, note)

        _old_unlink_episodes_from_dropped_tmdb_titles(self.session, title)

        if title.tmdb_title_links:
            _relink_episode(self.session, title)

        title.link_status = "Linked" if title.tmdb_title_links else "No Match Found"
        self.session.add(title)

    # TODO: Validate
    def _hand_linked_tmdb_title_ids(self) -> set[uuid.UUID]:
        episode_ids = [
            episode.id
            for episode in title_episodes(load_title_episodes(self.session, self.title))
        ]
        if not episode_ids:
            return set()

        tmdb_episode = aliased(Episode)
        return set(
            self.session.exec(
                select(Season.title_id)
                .join(tmdb_episode, col(Season.id) == col(tmdb_episode.season_id))
                .join(
                    EpisodeTmdbEpisode,
                    col(tmdb_episode.id) == col(EpisodeTmdbEpisode.tmdb_episode_id),
                )
                .join(Episode, col(Episode.id) == col(EpisodeTmdbEpisode.episode_id))
                .where(
                    col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
                    or_(
                        col(EpisodeTmdbEpisode.manual_tmdb_link).is_(True),
                        col(Episode.tmdb_episode_validated_at).is_not(None),
                    ),
                ),
            ).all(),
        )


# TODO: Validate
def link_new_title_to_tmdb(session: Session, title: Title) -> None:
    if title.link_status:
        msg = "link_new_title_to_tmdb should only be called on new titles."
        raise ValueError(msg)
    if title.source.key == TMDB_SOURCE_KEY:
        msg = "link_new_title_to_tmdb should not be called on TMDB titles."
        raise ValueError(msg)

    TitleLinker(session, title).relink()


# TODO: Validate
def link_title(session: Session, title: Title) -> None:
    if title.source.key == TMDB_SOURCE_KEY:
        _old_relink_episodes(session, title)
        return
    if not title.source.link_to_tmdb:
        return
    TitleLinker(session, title).relink()
