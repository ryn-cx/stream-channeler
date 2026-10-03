# TODO: Validate
from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy.orm import aliased
from sqlmodel import col, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.service.linking.details import (
    EpisodeDetails,
    LinkedEpisodeRow,
    MatchKind,
    SourceEpisodeDetails,
    SplitNameNormalizers,
    TmdbEpisodeDetails,
    link_combined_to_part,
)
from app.episodes.service.linking.numbers import (
    absolute_episode_number,
    episode_number,
    has_no_name,
    meaningless_name,
    number_to_episodes,
    same_number,
    season_and_episode_number,
    season_episode_name_tuple,
    set_absolute_numbers,
    stripped_name,
)
from app.episodes.service.linking.queries import (
    LoadedTitle,
    other_source_filters,
)
from app.episodes.service.linking.scoring import (
    agreed_matches,
    agreed_part_match,
    assign_best_matches,
    clear_two_way_match,
    combined_note,
    combined_two_way,
    required_gap,
    scored_part_matches,
    two_way_note,
)
from app.episodes.service.linking.text import (
    best_scores,
    listing_parts,
    split_name_parts,
)
from app.episodes.service.names.forms import (
    get_cased_episode_name,
    get_normalized_episode_name,
    plaintext,
)
from app.episodes.service.names.matching import (
    episode_number_name,
    similarity,
)
from app.episodes.service.names.vectors import TextMatcher
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.utils import tz_datetime

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable, Sequence

    import numpy  # noqa: ICN001
    from sqlmodel import Session


# TODO: Validate
def clips_season(episode: EpisodeDetails) -> bool:
    return (
        episode.season_number == 0
        and episode.season_name is not None
        and bool(re.fullmatch(r"Clips( from Season \d+)?", episode.season_name))
    )


# TODO: Validate
def extras_season(episode: EpisodeDetails) -> bool:
    return episode.season_number == 0 and episode.season_name == "Extras"


# TODO: Validate
def text_of_kinds(
    kinds: Sequence[MatchKind],
) -> Callable[[EpisodeDetails], str]:
    if MatchKind.TFIDF_DESCRIPTION in kinds or MatchKind.EMBEDDING_DESCRIPTION in kinds:
        return lambda episode: episode.description
    return lambda episode: episode.name_for_scoring


# TODO: Validate
class EpisodeLinker:
    # TODO: Validate
    def __init__(self, session: Session, linked_title: LoadedTitle) -> None:
        self.session = session
        self.linked_title = linked_title
        self.other_source_episodes: list[LinkedEpisodeRow] = []
        self.similarities: dict[tuple[str, str], float] = {}
        self.tmdb_numbers: dict[
            Callable[[EpisodeDetails], tuple[int, ...] | None],
            dict[uuid.UUID, tuple[int, ...] | None],
        ] = {}
        self.numbered_tmdb_episodes: dict[
            Callable[[EpisodeDetails], tuple[int, ...] | None],
            defaultdict[tuple[int, ...], list[TmdbEpisodeDetails]],
        ] = {}
        with session.no_autoflush:
            self._load_linked_tmdb_episodes_from_other_titles()
            self._init_episodes()
            self.id_to_tmdb_episode = {
                tmdb_episode.id: tmdb_episode for tmdb_episode in self.tmdb_episodes
            }

    # TODO: Validate
    def _similarity(self, text: str, other_text: str) -> float:
        key = (text, other_text) if text <= other_text else (other_text, text)
        score = self.similarities.get(key)
        if score is None:
            score = similarity(*key)
            self.similarities[key] = score
        return score

    # TODO: Validate
    def _tmdb_number(
        self,
        number_of: Callable[[EpisodeDetails], tuple[int, ...] | None],
        tmdb_episode: EpisodeDetails,
    ) -> tuple[int, ...] | None:
        numbers = self.tmdb_numbers.get(number_of)
        if numbers is None:
            numbers = {episode.id: number_of(episode) for episode in self.tmdb_episodes}
            self.tmdb_numbers[number_of] = numbers
        return numbers[tmdb_episode.id]

    # TODO: Validate
    def _numbered_tmdb_episodes(
        self,
        number_of: Callable[[EpisodeDetails], tuple[int, ...] | None],
    ) -> defaultdict[tuple[int, ...], list[TmdbEpisodeDetails]]:
        grouped = self.numbered_tmdb_episodes.get(number_of)
        if grouped is None:
            grouped = number_to_episodes(self.tmdb_episodes, number_of)
            self.numbered_tmdb_episodes[number_of] = grouped
        return grouped

    # TODO: Validate
    def _covers_one_part_only(
        self,
        text: str,
        candidate_text: str,
    ) -> bool:
        parts = listing_parts(text)
        if len(parts) < 2 or not candidate_text:  # noqa: PLR2004
            return False
        whole = self._similarity(text, candidate_text)
        return any(self._similarity(part, candidate_text) > whole for part in parts)

    # TODO: Validate
    def _load_linked_tmdb_episodes_from_other_titles(self) -> None:
        tmdb_title_ids = self.linked_title.tmdb_title_ids
        if not tmdb_title_ids:
            return
        other_title = aliased(Title)
        rows: Sequence[
            tuple[
                str | None,
                int | None,
                int | None,
                str | None,
                str | None,
                uuid.UUID,
            ]
        ] = self.session.exec(
            select(  # type: ignore[call-overload]
                col(Episode.name),
                col(Season.season_number),
                col(Episode.episode_number),
                col(other_title.name),
                col(Season.name),
                col(EpisodeTmdbEpisode.tmdb_episode_id),
            )
            .join(Season, onclause=col(Episode.season_id) == col(Season.id))
            .join(other_title, onclause=col(Season.title_id) == other_title.id)
            .join(
                TitleTmdbTitle,
                onclause=col(TitleTmdbTitle.title_id) == other_title.id,
            )
            .join(
                EpisodeTmdbEpisode,
                onclause=col(EpisodeTmdbEpisode.episode_id) == col(Episode.id),
            )
            .where(
                *other_source_filters(
                    other_title,
                    self.linked_title.id,
                    tmdb_title_ids,
                ),
                col(Episode.tmdb_episode_validated_at).is_not(None),
            ),
        ).all()
        self.other_source_episodes = [
            LinkedEpisodeRow(
                normalized,
                cased,
                season_number,
                episode_number,
                tmdb_episode_id,
            )
            for (
                name,
                season_number,
                episode_number,
                title_name,
                season_name,
                tmdb_episode_id,
            ) in rows
            if episode_number is not None
            and (
                normalized := get_normalized_episode_name(
                    name,
                    title_name,
                    season_name,
                )
            )
            and (
                cased := get_cased_episode_name(
                    name,
                    title_name,
                    season_name,
                )
            )
        ]

    # TODO: Validate
    def relink_titles(self) -> None:
        """Relink every episode that does not have a manual TMDB link."""
        with self.session.no_autoflush:
            # Existing validated links should always be highest priority because they
            # are known to be correct.
            self._link_existing_validated_links()
            self._link_validated_other_source_matches()

            # Perfect name and number matches are highest priority.
            self._link_matching_name_and_number()
            self._link_matching_name_and_absolute_number()
            self._link_matching_name_and_episode_number_to_absolute_number()

            self._link_fuzzy_other_source_matches()

            self._link_matching_normalized_name_and_number()
            self._link_matching_normalized_name_and_absolute_number()
            self._link_matching_normalized_name_and_episode_number_to_absolute_number()

            self._score_matches(
                lambda episode: episode.name_for_scoring,
                MatchKind.TFIDF_NAME,
                MatchKind.EMBEDDING_NAME,
            )
            self._score_matches(
                lambda episode: episode.description,
                MatchKind.TFIDF_DESCRIPTION,
                MatchKind.EMBEDDING_DESCRIPTION,
            )

            # Matching episode numbers
            self._link_scored_name_and_number()
            self._link_scored_name_and_absolute_number()
            self._link_scored_name_and_episode_number_to_absolute_number()
            self._link_matching_description_and_number()
            self._link_matching_description_and_absolute_number()
            self._link_matching_description_and_episode_number_to_absolute_number()
            self._link_matching_normalized_description_and_number()
            self._link_matching_normalized_description_and_absolute_number()
            self._link_matching_normalized_description_and_episode_number_to_absolute_number()
            self._link_scored_description_and_number()
            self._link_scored_description_and_absolute_number()
            self._link_scored_description_and_episode_number_to_absolute_number()

            self._link_unnamed_numbers()

            self._link_matching_name()
            self._link_matching_split_name()
            self._link_matching_normalized_name()
            self._link_matching_normalized_split_name()
            self._link_scored_split_names()
            self._link_reused_matching_name()

            self._link_clear_score_matches(
                (MatchKind.TFIDF_NAME, MatchKind.EMBEDDING_NAME),
            )

            self._link_clear_score_matches(
                (MatchKind.TFIDF_DESCRIPTION, MatchKind.EMBEDDING_DESCRIPTION),
            )

            self._link_scored_split_name_parts()

            # # The last remaining exact match linker

            # # Covers typos in names

            # # Try to re-use validated links from other sources if possible.
            # self._link_scored_validated_other_source_matches()

            # # Numbers are the same and it's the best match by far.

            self._link_scored_number_matches(
                (MatchKind.TFIDF_NAME, MatchKind.EMBEDDING_NAME),
            )

            # # Go back to the split episodes.

            # # Descriptions seem like they can be inconsistent and prone to being
            # # completely incorrect so they are not used until last.
            # self._link_matching_description()

            self._link_scored_number_matches(
                (MatchKind.TFIDF_DESCRIPTION, MatchKind.EMBEDDING_DESCRIPTION),
            )

            # # self._link_agreed_high_score_matches()
            # # self._link_perfect_two_way_matches()
            # # self._link_matching_description_twins()
            # # self._link_shared_description_matches()
            # # self._link_fuzzy_other_source_matches()
            # # self._link_absolute_number_matches()
            self._link_agreed_number_matches()
            self._link_fuzzy_name_scores()
            self._link_matching_name_twins()
            self._link_numbered_names()
            self._mark_absent_from_tmdb()
            self._save_links()

    # TODO: Validate
    def _init_episodes(self) -> None:
        self.episodes = [
            self._init_source_episode(episode, season, self.linked_title.name)
            for season in self.linked_title.active_children
            for episode in season.active_children
        ]
        self.tmdb_episodes = []
        for tmdb_title in self.linked_title.tmdb_titles:
            tmdb_title_episodes = [
                self._init_tmdb_episode(
                    episode,
                    season,
                    tmdb_title.name,
                    self.linked_title.name,
                )
                for season in tmdb_title.active_children
                for episode in season.active_children
            ]
            set_absolute_numbers(tmdb_title_episodes)
            self.tmdb_episodes.extend(tmdb_title_episodes)

        self.linkable_episodes = [
            episode for episode in self.episodes if not self._absent_from_tmdb(episode)
        ]

        # It's easier to set absolute numbers after every episode is initialized.
        set_absolute_numbers(self.episodes)

    # TODO: Validate
    @staticmethod
    def _init_source_episode(
        episode: Episode,
        season: Season,
        title_name: str | None,
    ) -> SourceEpisodeDetails:
        return SourceEpisodeDetails(
            model=episode,
            id=episode.id,
            key=episode.key,
            name=episode.name,
            description=episode.description or "",
            episode_number=episode.episode_number,
            season_number=season.season_number,
            title_name=title_name,
            season_name=season.name,
            tmdb_episode_validated_at=episode.tmdb_episode_validated_at,
        )

    # TODO: Validate
    @staticmethod
    def _init_tmdb_episode(
        episode: Episode,
        season: Season,
        title_name: str | None,
        series_name: str | None,
    ) -> TmdbEpisodeDetails:
        return TmdbEpisodeDetails(
            model=episode,
            id=episode.id,
            key=episode.key,
            name=episode.name,
            description=episode.description or "",
            episode_number=episode.episode_number,
            season_number=season.season_number,
            title_name=title_name,
            season_name=season.name,
            series_name=series_name,
        )

    # TODO: Validate
    def _link_existing_validated_links(self) -> None:
        """Link existing validated links.

        Linking the episodes (instead of ignoring episodes with validated linkes) makes
        it easier to track which episodes have links already linked to them."""
        for episode in self.episodes:
            if not episode.tmdb_episode_validated_at:
                continue
            for link in episode.model.tmdb_episode_links:
                # tmdb_episode will be None if TMDB's episode is deleted after an
                # episode is linked to it.
                if tmdb_episode := self.id_to_tmdb_episode.get(link.tmdb_episode_id):
                    if not link.note:
                        msg = f"Manual link for episode {episode.id} has no note."
                        raise ValueError(msg)
                    episode.link_to(tmdb_episode, link.note)

    # TODO: Validate
    def _unmatched_episodes(self) -> list[SourceEpisodeDetails]:
        return [
            episode for episode in self.linkable_episodes if not episode.linked_episodes
        ]

    # TODO: Validate
    @staticmethod
    def _linked_rows_of(episode: SourceEpisodeDetails) -> list[LinkedEpisodeRow]:
        if (
            not episode.normalized_name
            or episode.episode_number is None
            or episode.tmdb_episode_validated_at is None
        ):
            return []
        return [
            LinkedEpisodeRow(
                episode.normalized_name,
                episode.cased_name,
                episode.season_number,
                episode.episode_number,
                tmdb_episode.id,
            )
            for tmdb_episode in episode.linked_episodes
        ]

    # TODO: Validate
    def _same_title_linked_rows(self) -> list[LinkedEpisodeRow]:
        return [
            row for episode in self.episodes for row in self._linked_rows_of(episode)
        ]

    # TODO: Validate
    def _validated_tmdb_episode_ids_by_number_and_name(
        self,
    ) -> dict[tuple[int | None, int, str], set[uuid.UUID]]:
        by_number_and_name: dict[tuple[int | None, int, str], set[uuid.UUID]] = {}
        for row in [*self.other_source_episodes, *self._same_title_linked_rows()]:
            key = (row.season_number, row.episode_number, row.name)
            by_number_and_name.setdefault(key, set()).add(row.tmdb_episode_id)
        return by_number_and_name

    # TODO: Validate
    def _link_validated_other_source_matches(self) -> None:
        """Link episodes using the link information from already validated episodes
        that have the same season number, episode number and name.
        """
        tmdb_episode_ids_by_number_and_name = (
            self._validated_tmdb_episode_ids_by_number_and_name()
        )
        for episode in self._unmatched_episodes():
            key = season_episode_name_tuple(episode)
            if key is not None:
                self._link_other_source_candidates(
                    episode,
                    tmdb_episode_ids_by_number_and_name.get(key, set()),
                    "Automatic: Name, season and episode number match from another source",
                )

    # TODO: Validate
    def _episode_number_to_linked_episode(
        self,
    ) -> defaultdict[tuple[int | None, int], list[LinkedEpisodeRow]]:
        episode_number_to_linked_episode: defaultdict[
            tuple[int | None, int],
            list[LinkedEpisodeRow],
        ] = defaultdict(list)
        for row in [*self.other_source_episodes, *self._same_title_linked_rows()]:
            dict_key = (row.season_number, row.episode_number)
            episode_number_to_linked_episode[dict_key].append(row)
        return episode_number_to_linked_episode

    # TODO: Validate
    def _link_fuzzy_other_source_matches(self) -> None:
        """Link the episode using another already linked episode that has the same
        episode number and a name close enough to it.
        """
        episode_number_to_linked_episode = self._episode_number_to_linked_episode()
        for episode in self._unmatched_episodes():
            if not episode.normalized_name or episode.episode_number is None:
                continue

            dict_key = (episode.season_number, episode.episode_number)
            tmdb_episodes = episode_number_to_linked_episode[dict_key]
            tmdb_episode_similarities = [
                (
                    row.tmdb_episode_id,
                    self._similarity(episode.normalized_name, row.name),
                )
                for row in tmdb_episodes
            ]
            scores = best_scores(tmdb_episode_similarities)
            self._link_scored_other_source_candidates(episode, scores, "Fuzzy name")

    # TODO: Validate
    def _link_scored_validated_other_source_matches(self) -> None:
        rows = [*self.other_source_episodes, *self._same_title_linked_rows()]
        episodes = [
            episode
            for episode in self._unmatched_episodes()
            if episode.normalized_name and episode.episode_number is not None
        ]
        if not rows or not episodes:
            return
        matcher = TextMatcher([row.cased_name for row in rows])
        names = [episode.cased_name for episode in episodes]
        tfidf_scores = matcher.tfidf_scores_of(names)
        embedding_scores = matcher.embedding_scores_of(names)
        for episode, episode_tfidf_scores, episode_embedding_scores in zip(
            episodes,
            tfidf_scores,
            embedding_scores,
            strict=True,
        ):
            if episode.linked_episodes:
                continue
            scores = best_scores(
                (row.tmdb_episode_id, max(float(tfidf_score), float(embedding_score)))
                for row, tfidf_score, embedding_score in zip(
                    rows,
                    episode_tfidf_scores,
                    episode_embedding_scores,
                    strict=True,
                )
                if row.season_number == episode.season_number
                and row.episode_number == episode.episode_number
            )
            self._link_scored_other_source_candidates(
                episode,
                scores,
                "TF-IDF or embedding name",
            )

    # TODO: Validate
    def _link_scored_other_source_matches(
        self,
        scores_of: Callable[[TextMatcher, list[str]], numpy.ndarray],
        label: str,
    ) -> None:
        """Link episodes using another already linked episode with the same episode
        number, scoring the two names against each other to decide how close they
        are.
        """
        episodes = [
            episode
            for episode in self._unmatched_episodes()
            if episode.normalized_name and episode.episode_number is not None
        ]
        season_numbers = {episode.season_number for episode in episodes}
        cross_title_rows = set(self.other_source_episodes)
        rows = list(
            dict.fromkeys(
                [
                    *self.other_source_episodes,
                    *(
                        row
                        for row in self._same_title_linked_rows()
                        if row.season_number in season_numbers
                    ),
                ],
            ),
        )
        if not episodes or not rows:
            return
        matcher = TextMatcher([row.cased_name for row in rows])
        all_scores = scores_of(
            matcher,
            [episode.cased_name for episode in episodes],
        )
        for episode, episode_scores in zip(episodes, all_scores, strict=True):
            if episode.linked_episodes:
                continue
            scores = best_scores(
                (linked_row.tmdb_episode_id, float(score))
                for linked_row, score in zip(rows, episode_scores, strict=True)
                if linked_row.episode_number == episode.episode_number
                and (
                    linked_row in cross_title_rows
                    or linked_row.season_number == episode.season_number
                )
            )
            self._link_scored_other_source_candidates(episode, scores, label)

    # TODO: Validate
    def _link_scored_other_source_candidates(
        self,
        episode: SourceEpisodeDetails,
        scores: dict[uuid.UUID, float],
        label: str,
    ) -> None:
        """Link the episode to the TMDB episode the scores point at, as long as
        something scored at least 90%.
        """
        matched = {
            tmdb_episode_id: score
            for tmdb_episode_id, score in scores.items()
            if score >= 0.9  # noqa: PLR2004
        }
        if not matched:
            return
        self._link_other_source_candidates(
            episode,
            set(matched),
            f"Automatic: {label} ({round(max(matched.values()) * 100)}%) and episode "
            "number match on another source",
        )

    # TODO: Validate
    def _link_other_source_candidates(
        self,
        episode: SourceEpisodeDetails,
        tmdb_episode_ids: set[uuid.UUID],
        note: str,
    ) -> None:
        """Link the episode when everything found on the other sources points at the
        one TMDB episode.
        """
        matches = [
            self.id_to_tmdb_episode[tmdb_episode_id]
            for tmdb_episode_id in tmdb_episode_ids
            if tmdb_episode_id in self.id_to_tmdb_episode
        ]
        if len(matches) != 1:
            return
        episode.link_to(matches[0], note)

    # TODO: Validate
    def _link_matching_name_and_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Name, season and episode number match",
        )

    # TODO: Validate
    def _link_matching_name_and_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Name and absolute number match",
        )

    # TODO: Validate
    def _link_matching_name_and_episode_number_to_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            episode_number,
            absolute_episode_number,
            "Automatic: Name and absolute episode number match",
        )

    # TODO: Validate
    def _link_matching_normalized_name_and_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Fuzzy name, season and episode number match",
            plaintext,
        )

    # TODO: Validate
    def _link_matching_normalized_name_and_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Fuzzy name and absolute number match",
            plaintext,
        )

    # TODO: Validate
    def _link_matching_normalized_name_and_episode_number_to_absolute_number(
        self,
    ) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.normalized_name,
            episode_number,
            absolute_episode_number,
            "Automatic: Fuzzy name and absolute episode number match",
            plaintext,
        )

    # TODO: Validate
    def _link_scored_name_and_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.normalized_name,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Name ({score}%), season and episode number match",
        )

    # TODO: Validate
    def _link_scored_name_and_absolute_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.normalized_name,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Name ({score}%) and absolute number match",
        )

    # TODO: Validate
    def _link_scored_name_and_episode_number_to_absolute_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.normalized_name,
            episode_number,
            absolute_episode_number,
            "Automatic: Name ({score}%) and absolute episode number match",
        )

    # TODO: Validate
    def _link_matching_description_and_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Description, season and episode number match",
            str.casefold,
        )

    # TODO: Validate
    def _link_matching_description_and_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Description and absolute number match",
            str.casefold,
        )

    # TODO: Validate
    def _link_matching_description_and_episode_number_to_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            episode_number,
            absolute_episode_number,
            "Automatic: Description and absolute episode number match",
            str.casefold,
        )

    # TODO: Validate
    def _link_matching_normalized_description_and_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Fuzzy description, season and episode number match",
            plaintext,
        )

    # TODO: Validate
    def _link_matching_normalized_description_and_absolute_number(self) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Fuzzy description and absolute number match",
            plaintext,
        )

    # TODO: Validate
    def _link_matching_normalized_description_and_episode_number_to_absolute_number(
        self,
    ) -> None:
        self._link_matching_text_and_numbers(
            lambda episode: episode.description,
            episode_number,
            absolute_episode_number,
            "Automatic: Fuzzy description and absolute episode number match",
            plaintext,
        )

    # TODO: Validate
    def _link_scored_description_and_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.description,
            season_and_episode_number,
            season_and_episode_number,
            "Automatic: Description ({score}%), season and episode number match",
        )

    # TODO: Validate
    def _link_scored_description_and_absolute_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.description,
            absolute_episode_number,
            absolute_episode_number,
            "Automatic: Description ({score}%) and absolute number match",
        )

    # TODO: Validate
    def _link_scored_description_and_episode_number_to_absolute_number(self) -> None:
        self._link_scored_text_and_numbers(
            lambda episode: episode.description,
            episode_number,
            absolute_episode_number,
            "Automatic: Description ({score}%) and absolute episode number match",
        )

    # TODO: Validate
    def _link_matching_text_and_numbers(
        self,
        attribute_accessor: Callable[[EpisodeDetails], str],
        episode_number_function: Callable[[EpisodeDetails], tuple[int, ...] | None],
        tmdb_number_function: Callable[[EpisodeDetails], tuple[int, ...] | None],
        note: str,
        normalize: Callable[[str], str] = str,
    ) -> None:
        number_to_tmdb_episodes = self._numbered_tmdb_episodes(tmdb_number_function)
        for episode in self._unmatched_episodes():
            number = episode_number_function(episode)
            normalized_text = normalize(attribute_accessor(episode))
            if number is None or not normalized_text:
                continue
            matches = [
                tmdb_episode
                for tmdb_episode in number_to_tmdb_episodes[number]
                if normalize(attribute_accessor(tmdb_episode)) == normalized_text
            ]
            if len(matches) != 1:
                continue
            episode.link_to(matches[0], note)

    # TODO: Validate
    def _link_scored_text_and_numbers(
        self,
        attribute_accessor: Callable[[EpisodeDetails], str],
        episode_number_function: Callable[[EpisodeDetails], tuple[int, ...] | None],
        tmdb_number_function: Callable[[EpisodeDetails], tuple[int, ...] | None],
        note_template: str,
    ) -> None:
        for episode in self._unmatched_episodes():
            number = episode_number_function(episode)
            text = attribute_accessor(episode)
            if number is None or not text:
                continue
            scored = sorted(
                (
                    (
                        self._similarity(text, attribute_accessor(tmdb_episode)),
                        tmdb_episode,
                    )
                    for tmdb_episode in self.tmdb_episodes
                    if attribute_accessor(tmdb_episode)
                    and self._sharable_tmdb_episode(episode, tmdb_episode)
                ),
                key=lambda scored_episode: scored_episode[0],
                reverse=True,
            )
            if not scored:
                continue
            score, tmdb_episode = scored[0]
            if self._tmdb_number(tmdb_number_function, tmdb_episode) != number:
                continue
            if self._covers_one_part_only(text, attribute_accessor(tmdb_episode)):
                continue
            runner_up = max(
                (
                    other_score
                    for other_score, other_episode in scored[1:]
                    if self._tmdb_number(tmdb_number_function, other_episode) == number
                ),
                default=0.0,
            )
            if score < 0.6:  # noqa: PLR2004
                continue
            if score - runner_up < required_gap(score):
                continue
            episode.link_to(
                tmdb_episode,
                note_template.format(score=round(score * 100)),
            )

    # TODO: Validate
    def _link_matching_split_name(self) -> None:
        self._link_split_names(
            SplitNameNormalizers(
                lambda episode: episode.normalized_name,
                "Split name",
            ),
        )

    # TODO: Validate
    def _link_matching_normalized_split_name(self) -> None:
        self._link_split_names(
            SplitNameNormalizers(
                lambda episode: episode.normalized_name,
                "Fuzzy split name",
                plaintext,
            ),
        )

    # TODO: Validate
    def _link_matching_name(self) -> None:
        self._link_matching_text(
            lambda episode: episode.normalized_name,
            "Exact name",
        )

    # TODO: Validate
    def _link_matching_normalized_name(self) -> None:
        self._link_matching_text(
            lambda episode: episode.normalized_name,
            "Fuzzy name",
            plaintext,
        )

    # TODO: Validate
    def _link_reused_matching_name(self) -> None:
        self._link_reused_matching_text("Exact name")
        self._link_reused_matching_text("Fuzzy name", plaintext)

    # TODO: Validate
    def _link_reused_matching_text(
        self,
        label: str,
        normalize: Callable[[str], str] = str,
    ) -> None:
        normalized_name_to_tmdb_episodes: defaultdict[str, list[TmdbEpisodeDetails]] = (
            defaultdict(list)
        )
        for tmdb_episode in self.tmdb_episodes:
            normalized = normalize(tmdb_episode.normalized_name)
            if normalized:
                normalized_name_to_tmdb_episodes[normalized].append(tmdb_episode)
        for episode in self._unmatched_episodes():
            normalized = normalize(episode.normalized_name)
            if not normalized:
                continue
            candidates = normalized_name_to_tmdb_episodes[normalized]
            if len(candidates) != 1:
                continue
            if not self._sharable_tmdb_episode(episode, candidates[0]):
                continue
            episode.link_to(
                candidates[0],
                f"Automatic: {label} match on an already used episode",
            )

    # TODO: Validate
    @staticmethod
    def _sharable_tmdb_episode(
        episode: SourceEpisodeDetails,
        tmdb_episode: TmdbEpisodeDetails,
    ) -> bool:
        if not tmdb_episode.linked_episodes:
            return True
        if not same_number(episode, tmdb_episode):
            return False
        return all(
            (
                linked.season_number == episode.season_number
                and linked.episode_number == episode.episode_number
            )
            or linked.name == episode.name
            for linked in tmdb_episode.linked_episodes
        )

    # TODO: Validate
    def _link_matching_description(self) -> None:
        self._link_matching_text(
            lambda episode: episode.description,
            "Exact description",
            str.casefold,
        )

    # TODO: Validate
    @staticmethod
    def _normalized_name_to_episodes[DetailsT: EpisodeDetails](
        episodes: Sequence[DetailsT],
        text_of: Callable[[DetailsT], str],
        normalize: Callable[[str], str],
    ) -> defaultdict[str, list[DetailsT]]:
        """Group the episodes that still need a link by their key, skipping the ones that
        have no key.
        """
        grouped: defaultdict[str, list[DetailsT]] = defaultdict(list)
        for episode in episodes:
            if episode.linked_episodes:
                continue
            normalized = normalize(text_of(episode))
            if normalized:
                grouped[normalized].append(episode)
        return grouped

    # TODO: Validate
    def _link_matching_text(
        self,
        attribute_accessor: Callable[[EpisodeDetails], str],
        label: str,
        normalize: Callable[[str], str] = str,
    ) -> None:
        ambiguous_groups: list[
            tuple[list[SourceEpisodeDetails], list[TmdbEpisodeDetails]]
        ] = []
        normalized_name_to_tmdb_episodes = self._normalized_name_to_episodes(
            self.tmdb_episodes,
            attribute_accessor,
            normalize,
        )
        normalized_name_to_source_episodes = self._normalized_name_to_episodes(
            self.linkable_episodes,
            attribute_accessor,
            normalize,
        )
        items = normalized_name_to_source_episodes.items()
        for normalized_episode_name, same_name_source_episodes in items:
            # If no matching names are found nothing needs to be done.
            tmdb_episodes = normalized_name_to_tmdb_episodes[normalized_episode_name]
            if not tmdb_episodes:
                continue

            numbers = {
                season_and_episode_number(episode)
                for episode in same_name_source_episodes
            }
            sharable = len(numbers) == 1 and None not in numbers
            if len(tmdb_episodes) == 1 and (
                sharable or len(same_name_source_episodes) == 1
            ):
                for episode in same_name_source_episodes:
                    episode.link_to(tmdb_episodes[0], f"Automatic: {label} match")
                continue
            ambiguous_groups.append((same_name_source_episodes, tmdb_episodes))
        self._link_matching_text_by_number(ambiguous_groups, label)

    # TODO: Validate
    def _link_matching_text_by_number(
        self,
        ambiguous_groups: list[
            tuple[list[SourceEpisodeDetails], list[TmdbEpisodeDetails]]
        ],
        label: str,
    ) -> None:
        """Link episodes whose keys matched but where there was more than one to pick
        from, using their numbers to pick. Every key is taken through one way of
        numbering before any key moves on to the next, so that a key matched by a
        weaker number cannot take an episode a later key would have matched on a
        stronger one.
        """
        for episodes, tmdb_episodes in ambiguous_groups:
            self._link_unique_numbers(
                episodes,
                tmdb_episodes,
                season_and_episode_number,
                season_and_episode_number,
                f"Automatic: {label} and episode number match",
            )
        for episodes, tmdb_episodes in ambiguous_groups:
            self._link_unique_numbers(
                episodes,
                tmdb_episodes,
                absolute_episode_number,
                absolute_episode_number,
                f"Automatic: {label} and absolute number match",
            )
        for episodes, tmdb_episodes in ambiguous_groups:
            self._link_unique_numbers(
                episodes,
                tmdb_episodes,
                episode_number,
                absolute_episode_number,
                f"Automatic: {label} and absolute episode number match",
            )

    # TODO: Validate
    def _link_unique_numbers(
        self,
        episodes: list[SourceEpisodeDetails],
        tmdb_episodes: list[TmdbEpisodeDetails],
        number_of: Callable[[EpisodeDetails], tuple[int, ...] | None],
        tmdb_number_of: Callable[[EpisodeDetails], tuple[int, ...] | None],
        note: str,
    ) -> None:
        """Link an episode to a TMDB episode when a number belongs to exactly one
        episode on each side.
        """
        number_to_tmdb_episodes = number_to_episodes(tmdb_episodes, tmdb_number_of)
        for number, numbered_episodes in number_to_episodes(
            [episode for episode in episodes if not episode.linked_episodes],
            number_of,
        ).items():
            candidates = number_to_tmdb_episodes[number]
            if len(numbered_episodes) != 1 or len(candidates) != 1:
                continue
            numbered_episodes[0].link_to(candidates[0], note)

    # TODO: Validate
    def _link_unnamed_numbers(self) -> None:
        number_to_tmdb_episodes = self._numbered_tmdb_episodes(
            season_and_episode_number,
        )
        every_stripped_name_is_empty = all(
            not stripped_name(episode) for episode in self.linkable_episodes
        )
        for episode in self._unmatched_episodes():
            if not has_no_name(
                episode,
                every_stripped_name_is_empty=every_stripped_name_is_empty,
            ):
                continue
            number = season_and_episode_number(episode)
            if number is None:
                continue
            matches = number_to_tmdb_episodes[number]
            if len(matches) != 1:
                continue
            episode.link_to(
                matches[0],
                "Automatic: Episode has no name so the season and episode number are "
                "the only match",
            )

    # TODO: Validate
    def _link_agreed_number_matches(self) -> None:
        for episode in self._unmatched_episodes():
            if len(episode.matches) != len(MatchKind):
                continue
            tmdb_episode = self._agreed_match(episode, 0.07)
            if tmdb_episode is None:
                continue
            if not same_number(episode, tmdb_episode):
                continue
            episode.link_to(
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with the episode number"),
            )

    # TODO: Validate
    def _link_fuzzy_name_scores(self) -> None:
        for episode in self._unmatched_episodes():
            if not episode.normalized_name:
                continue
            name = episode.normalized_name
            scored = sorted(
                (
                    (
                        self._similarity(name, tmdb_episode.normalized_name),
                        tmdb_episode,
                    )
                    for tmdb_episode in self.tmdb_episodes
                    if not tmdb_episode.linked_episodes and tmdb_episode.normalized_name
                ),
                key=lambda scored_episode: scored_episode[0],
                reverse=True,
            )
            if not scored:
                continue
            score, tmdb_episode = scored[0]
            runner_up = scored[1][0] if len(scored) > 1 else 0.0
            if score < 0.9:  # noqa: PLR2004
                continue
            if score - runner_up < required_gap(score):
                continue
            episode.link_to(
                tmdb_episode,
                f"Automatic: Fuzzy name ({round(score * 100)}%) two-way match clear of "
                f"everything else",
            )

    # TODO: Validate
    def _link_matching_name_twins(self) -> None:
        for episode in self._unmatched_episodes():
            number = season_and_episode_number(episode)
            if number is None or not episode.normalized_name:
                continue
            linked_ids = {
                tuple(
                    sorted(tmdb_episode.id for tmdb_episode in twin.linked_episodes),
                )
                for twin in self.episodes
                if twin is not episode
                and twin.linked_episodes
                and season_and_episode_number(twin) == number
                and self._similarity(episode.normalized_name, twin.normalized_name)
                >= 0.9  # noqa: PLR2004
            }
            if len(linked_ids) != 1:
                continue
            for tmdb_episode_id in next(iter(linked_ids)):
                episode.link_to(
                    self.id_to_tmdb_episode[tmdb_episode_id],
                    "Automatic: Season and episode number match with another episode "
                    "of the same name",
                )

    # TODO: Validate
    def _link_numbered_names(self) -> None:
        number_to_tmdb_episodes = self._numbered_tmdb_episodes(
            season_and_episode_number,
        )
        for episode in self._unmatched_episodes():
            named_number = episode_number_name(episode.name)
            if named_number is None or episode.season_number is None:
                continue
            matches = number_to_tmdb_episodes[(episode.season_number, named_number)]
            if len(matches) != 1:
                continue
            episode.link_to(
                matches[0],
                f"Automatic: Name is episode {named_number} of the season",
            )

    # TODO: Validate
    def _link_absolute_number_matches(self) -> None:
        """Link an episode to the TMDB episode sitting at the same point in the title,
        for a site that numbers its episodes straight through rather than per season.
        The number has to be the only one of its kind on both sides, and the names have
        to back it up.
        """
        number_to_tmdb_episodes = self._numbered_tmdb_episodes(
            absolute_episode_number,
        )
        for number, numbered_episodes in number_to_episodes(
            self._unmatched_episodes(),
            episode_number,
        ).items():
            candidates = number_to_tmdb_episodes[number]
            if len(numbered_episodes) != 1 or len(candidates) != 1:
                continue
            episode = numbered_episodes[0]
            tmdb_episode = candidates[0]
            both_unnamed = meaningless_name(episode) and meaningless_name(
                tmdb_episode,
            )
            if not both_unnamed and not agreed_matches(episode, tmdb_episode):
                continue
            episode.link_to(
                tmdb_episode,
                "Automatic: Absolute episode number match backed up by the names",
            )

    # TODO: Validate
    def _link_matching_description_twins(self) -> None:
        linked_tmdb_episode_ids: defaultdict[
            tuple[str, tuple[int, ...]],
            set[uuid.UUID],
        ] = defaultdict(set)
        for episode in self.episodes:
            normalized = plaintext(episode.description)
            numbered = season_and_episode_number(episode)
            if not normalized or numbered is None:
                continue
            for tmdb_episode in episode.linked_episodes:
                linked_tmdb_episode_ids[(normalized, numbered)].add(
                    tmdb_episode.id,
                )
        for episode in self._unmatched_episodes():
            normalized = plaintext(episode.description)
            numbered = season_and_episode_number(episode)
            if not normalized or numbered is None:
                continue
            self._link_other_source_candidates(
                episode,
                linked_tmdb_episode_ids[(normalized, numbered)],
                "Automatic: Description and episode number match on another episode",
            )

    # TODO: Validate
    def _link_shared_description_matches(self) -> None:
        normalized_to_tmdb_episodes: defaultdict[str, list[TmdbEpisodeDetails]] = (
            defaultdict(list)
        )
        for tmdb_episode in self.tmdb_episodes:
            normalized = plaintext(tmdb_episode.description)
            if normalized:
                normalized_to_tmdb_episodes[normalized].append(tmdb_episode)
        for episode in self._unmatched_episodes():
            normalized = plaintext(episode.description)
            if not normalized:
                continue
            matches = [
                tmdb_episode
                for tmdb_episode in normalized_to_tmdb_episodes[normalized]
                if same_number(episode, tmdb_episode)
            ]
            if len(matches) != 1:
                continue
            episode.link_to(
                matches[0],
                "Automatic: Description and episode number match",
            )

    # TODO: Validate
    def _link_split_names(self, normalizers: SplitNameNormalizers) -> None:
        """Link names that list several episodes at once, in both directions, since
        either side can be the one doing the listing.
        """
        self._link_combined_names(
            self.linkable_episodes,
            self.tmdb_episodes,
            normalizers,
        )
        self._link_combined_names(
            self.tmdb_episodes,
            self.linkable_episodes,
            normalizers,
        )

    # TODO: Validate
    def _link_scored_split_names(self) -> None:
        """Link names that list several episodes at once by scoring their parts, for the
        parts that matching on the name alone could not place. Runs in both directions,
        since either side can be the one doing the listing.
        """
        self._link_scored_combined_names(self.linkable_episodes, self.tmdb_episodes)
        self._link_scored_combined_names(self.tmdb_episodes, self.linkable_episodes)

    # TODO: Validate
    def _link_scored_combined_names(
        self,
        combined_episodes: Sequence[EpisodeDetails],
        part_episodes: Sequence[EpisodeDetails],
    ) -> None:
        """Score every part of every combined name still waiting against every episode
        still waiting, and link a name whose parts each came back with an episode of
        their own.
        """
        pending = [
            (episode, split_name_parts(episode.name_for_scoring))
            for episode in combined_episodes
            if not episode.linked_episodes
        ]
        pending = [(episode, parts) for episode, parts in pending if len(parts) > 1]
        candidates = [
            episode
            for episode in part_episodes
            if not episode.linked_episodes and episode.name_for_scoring
        ]
        if not pending or not candidates:
            return
        matcher = TextMatcher(
            [episode.name_for_scoring for episode in candidates],
        )
        texts = [part for _episode, parts in pending for part in parts]
        tfidf = matcher.tfidf_scores_of(texts)
        embedding = matcher.embedding_scores_of(texts)
        note = "Automatic: Scored split name match"
        row = 0
        for combined_episode, parts in pending:
            rows = range(row, row + len(parts))
            row += len(parts)
            if combined_episode.linked_episodes:
                continue
            matches = scored_part_matches(tfidf, embedding, rows, candidates)
            if matches is None:
                continue
            if any(
                clips_season(match) != clips_season(combined_episode)
                for match in matches
            ):
                continue
            for match in matches:
                link_combined_to_part(combined_episode, match, note)

    # TODO: Validate
    def _link_scored_split_name_parts(self) -> None:
        self._link_scored_combined_name_parts(
            self.linkable_episodes,
            self.tmdb_episodes,
        )
        self._link_scored_combined_name_parts(
            self.tmdb_episodes,
            self.linkable_episodes,
        )

    # TODO: Validate
    def _link_scored_combined_name_parts(
        self,
        combined_episodes: Sequence[EpisodeDetails],
        part_episodes: Sequence[EpisodeDetails],
    ) -> None:
        """Link the parts of a combined name that scored onto an episode of their own,
        leaving the parts that did not for something else to place.
        """
        pending = [
            (episode, split_name_parts(episode.name_for_scoring))
            for episode in combined_episodes
            if not episode.linked_episodes
        ]
        pending = [(episode, parts) for episode, parts in pending if len(parts) > 1]
        candidates = [
            episode
            for episode in part_episodes
            if not episode.linked_episodes and episode.name_for_scoring
        ]
        if not pending or not candidates:
            return
        matcher = TextMatcher(
            [episode.name_for_scoring for episode in candidates],
        )
        texts = [part for _episode, parts in pending for part in parts]
        tfidf = matcher.tfidf_scores_of(texts)
        embedding = matcher.embedding_scores_of(texts)
        note = "Automatic: Scored split name part match"
        row = 0
        for combined_episode, parts in pending:
            rows = range(row, row + len(parts))
            row += len(parts)
            for part_row in rows:
                match = agreed_part_match(tfidf, embedding, part_row, candidates)
                if match is None or match.linked_episodes:
                    continue
                if clips_season(match) != clips_season(combined_episode):
                    continue
                link_combined_to_part(combined_episode, match, note)

    # TODO: Validate
    def _link_combined_names(
        self,
        combined_episodes: Sequence[EpisodeDetails],
        part_episodes: Sequence[EpisodeDetails],
        normalizers: SplitNameNormalizers,
    ) -> None:
        """Link an episode whose name lists several episodes to each of the episodes it
        names.
        """
        normalized_to_part_episodes = self._normalized_name_to_episodes(
            part_episodes,
            normalizers.text_of,
            normalizers.normalize,
        )
        note = f"Automatic: {normalizers.label} match"
        for combined_episode in combined_episodes:
            if combined_episode.linked_episodes:
                continue
            parts = split_name_parts(combined_episode.normalized_name)
            if len(parts) < 2:  # noqa: PLR2004
                continue
            matches = self._combined_name_matches(
                parts,
                normalized_to_part_episodes,
                normalizers.normalize,
            )
            if matches is None:
                continue
            for match in matches:
                link_combined_to_part(combined_episode, match, note)

    # TODO: Validate
    def _combined_name_matches[DetailsT: EpisodeDetails](
        self,
        parts: list[str],
        normalized_to_part_episodes: defaultdict[str, list[DetailsT]],
        normalize_part: Callable[[str], str],
    ) -> list[DetailsT] | None:
        """Find the episode each part of a combined name refers to, or nothing when any
        part does not land on exactly one episode that still needs a link.
        """
        matches: list[DetailsT] = []
        for part in parts:
            normalized = normalize_part(part)
            if not normalized:
                return None
            candidates = [
                candidate
                for candidate in normalized_to_part_episodes[normalized]
                if not candidate.linked_episodes
                and not any(match is candidate for match in matches)
            ]
            if len(candidates) != 1:
                return None
            matches.append(candidates[0])
        return matches

    # TODO: Validate
    def _mark_absent_from_tmdb(self) -> None:
        now = tz_datetime.now()
        for episode in self.episodes:
            if episode.model.tmdb_absent_at is not None and episode.linked_episodes:
                episode.model.tmdb_absent_at = None
                episode.model.tmdb_episode_validated_at = None
                episode.tmdb_episode_validated_at = None
                continue
            if episode.tmdb_episode_validated_at is not None:
                continue
            if not self._absent_from_tmdb(episode) and not extras_season(episode):
                continue
            if episode.linked_episodes:
                episode.model.tmdb_absent_at = None
            elif episode.model.tmdb_absent_at is None:
                episode.model.tmdb_absent_at = now

    # TODO: Validate
    @staticmethod
    def _absent_from_tmdb(episode: SourceEpisodeDetails) -> bool:
        if clips_season(episode):
            return True
        return episode.name is not None and bool(
            re.search(r"\bpv\b|\btrailer\b", episode.name, re.IGNORECASE),
        )

    # TODO: Validate
    def _save_links(self) -> None:
        for episode in self.episodes:
            episode.save_links()

    # TODO: Validate
    def _two_way_matches(
        self,
        episode: EpisodeDetails,
        *,
        perfect_only: bool = False,
    ) -> list[EpisodeDetails]:
        """Return the TMDB episodes that picked this episode as their best match while
        it picked them back.
        """
        matches: list[EpisodeDetails] = []
        for kind in MatchKind:
            best = episode.matches.get(kind)
            if best is None or not best.valid:
                continue
            if perfect_only and round(best.score, 6) < 1:
                continue
            mutual = best.episode.matches.get(kind)
            if mutual is None or not mutual.valid or mutual.episode is not episode:
                continue
            if best.episode not in matches:
                matches.append(best.episode)
        return matches

    # TODO: Validate
    def _link_scored_number_matches(self, kinds: Sequence[MatchKind]) -> None:
        for episode in self._unmatched_episodes():
            two_way = combined_two_way(episode, kinds)
            if two_way is None:
                continue
            combined = two_way[0]
            if not same_number(episode, combined.episode):
                continue
            episode.link_to(
                combined.episode,
                combined_note(combined, "match with episode number"),
            )

    # TODO: Validate
    def _link_clear_score_matches(self, kinds: Sequence[MatchKind]) -> None:
        attribute_accessor = text_of_kinds(kinds)
        for episode in self._unmatched_episodes():
            combined = clear_two_way_match(episode, kinds)
            if combined is None:
                continue
            if self._covers_one_part_only(
                attribute_accessor(episode),
                attribute_accessor(combined.episode),
            ):
                continue
            episode.link_to(
                combined.episode,
                combined_note(combined, "two-way match clear of everything else"),
            )

    # TODO: Validate
    def _link_agreed_high_score_matches(self) -> None:
        """Link an episode and a TMDB episode that picked each other at 90% or better
        on every way they were scored.
        """
        for episode in self.episodes:
            if episode.linked_episodes:
                continue
            tmdb_episode = self._agreed_match(episode, 0.9)
            if tmdb_episode is None or tmdb_episode.linked_episodes:
                continue
            episode.link_to(
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with a high score"),
            )

    # TODO: Validate
    def _agreed_match(
        self,
        episode: EpisodeDetails,
        minimum_score: float,
    ) -> EpisodeDetails | None:
        """Return the TMDB episode that every way of scoring above the given score
        agrees on, or nothing when they disagree or anything tied.
        """
        agreed: EpisodeDetails | None = None
        for kind in MatchKind:
            best = episode.matches.get(kind)
            if best is None or best.score < minimum_score:
                continue
            if not best.valid:
                return None
            mutual = best.episode.matches.get(kind)
            if mutual is None or not mutual.valid or mutual.episode is not episode:
                return None
            if agreed is not None and agreed is not best.episode:
                return None
            agreed = best.episode
        return agreed

    # TODO: Validate
    def _link_perfect_two_way_matches(self) -> None:
        """Link an episode and a TMDB episode that picked each other with a perfect
        score and picked nothing else.
        """
        for episode in self.episodes:
            if episode.linked_episodes:
                continue
            matches = self._two_way_matches(episode, perfect_only=True)
            if len(matches) != 1:
                continue
            tmdb_episode = matches[0]
            if tmdb_episode.linked_episodes:
                continue
            if self._two_way_matches(tmdb_episode, perfect_only=True) != [episode]:
                continue
            episode.link_to(
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with a perfect score"),
            )

    # TODO: Validate
    def _score_matches(
        self,
        text_of: Callable[[EpisodeDetails], str],
        tfidf_kind: MatchKind,
        embedding_kind: MatchKind,
    ) -> None:
        """Score every episode that still needs a link against every TMDB episode that
        still needs one, by TF-IDF and by embedding, and keep each one's best.
        """
        episodes = [
            episode
            for episode in self.linkable_episodes
            if not episode.linked_episodes and text_of(episode)
        ]
        tmdb_episodes = [
            tmdb_episode
            for tmdb_episode in self.tmdb_episodes
            if not tmdb_episode.linked_episodes and text_of(tmdb_episode)
        ]
        if not episodes or not tmdb_episodes:
            return

        matcher = TextMatcher([text_of(episode) for episode in episodes])
        tmdb_texts = [text_of(tmdb_episode) for tmdb_episode in tmdb_episodes]
        assign_best_matches(
            episodes,
            tmdb_episodes,
            matcher.tfidf_scores_of(tmdb_texts),
            tfidf_kind,
        )
        assign_best_matches(
            episodes,
            tmdb_episodes,
            matcher.embedding_scores_of(tmdb_texts),
            embedding_kind,
        )
