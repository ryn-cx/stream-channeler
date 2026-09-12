# TODO: Validate
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.episodes.models import EpisodeTmdbEpisode
from app.episodes.service.numbering import absolute_numbers
from app.episodes.text_matching import TextMatcher

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy  # noqa: ICN001
    from sqlmodel import Session

    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.titles.models import Title


# TODO: Validate
@dataclass(slots=True)
class EpisodeRecord:
    model: Episode
    key: str
    name: str | None
    description: str | None
    episode_number: int | None
    season_number: int | None
    absolute_number: int | None = None
    linked_episode: EpisodeRecord | None = None
    link_note: str | None = None
    tfidf_name_match: EpisodeMatch | None = None
    embedding_name_match: EpisodeMatch | None = None
    tfidf_description_match: EpisodeMatch | None = None
    embedding_description_match: EpisodeMatch | None = None


# TODO: Validate
@dataclass(slots=True)
class EpisodeMatch:
    score: float
    episode: EpisodeRecord
    valid: bool


# TODO: Validate
def episode_record(episode: Episode, season: Season) -> EpisodeRecord:
    return EpisodeRecord(
        model=episode,
        key=episode.key,
        name=episode.name,
        description=episode.description,
        episode_number=episode.episode_number,
        season_number=season.season_number,
    )


# TODO: Validate
def match_categories(
    episode: EpisodeRecord,
) -> tuple[tuple[str, EpisodeMatch | None], ...]:
    return (
        ("TF-IDF name", episode.tfidf_name_match),
        ("Embedding name", episode.embedding_name_match),
        ("TF-IDF description", episode.tfidf_description_match),
        ("Embedding description", episode.embedding_description_match),
    )


# TODO: Validate
def tfidf_name_match(episode: EpisodeRecord) -> EpisodeMatch | None:
    return episode.tfidf_name_match


# TODO: Validate
def embedding_name_match(episode: EpisodeRecord) -> EpisodeMatch | None:
    return episode.embedding_name_match


# TODO: Validate
def tfidf_description_match(episode: EpisodeRecord) -> EpisodeMatch | None:
    return episode.tfidf_description_match


# TODO: Validate
def embedding_description_match(episode: EpisodeRecord) -> EpisodeMatch | None:
    return episode.embedding_description_match


# TODO: Validate
def set_tfidf_name_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.tfidf_name_match = match


# TODO: Validate
def set_embedding_name_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.embedding_name_match = match


# TODO: Validate
def set_tfidf_description_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.tfidf_description_match = match


# TODO: Validate
def set_embedding_description_match(
    episode: EpisodeRecord,
    match: EpisodeMatch,
) -> None:
    episode.embedding_description_match = match


# TODO: Validate
def agreed_matches(
    episode: EpisodeRecord,
    tmdb_episode: EpisodeRecord,
) -> list[tuple[str, EpisodeMatch]]:
    agreed: list[tuple[str, EpisodeMatch]] = []
    for index, (label, best) in enumerate(match_categories(episode)):
        if best is None or not best.valid or best.episode is not tmdb_episode:
            continue
        mutual = match_categories(tmdb_episode)[index][1]
        if mutual is None or not mutual.valid or mutual.episode is not episode:
            continue
        agreed.append((label, best))
    return agreed


# TODO: Validate
def two_way_note(
    episode: EpisodeRecord,
    tmdb_episode: EpisodeRecord,
    reason: str,
) -> str:
    labels = [
        f"{label} ({round(match.score * 100)}%)"
        for label, match in agreed_matches(episode, tmdb_episode)
    ]
    return f"Automatic: {', '.join(labels)} two-way match {reason}"


# TODO: Validate
def assign_best_matches(
    episodes: list[EpisodeRecord],
    tmdb_episodes: list[EpisodeRecord],
    scores: numpy.ndarray,
    set_match: Callable[[EpisodeRecord, EpisodeMatch], None],
) -> None:
    for tmdb_episode, row in zip(tmdb_episodes, scores, strict=True):
        episode_index = int(row.argmax())
        score = float(row[episode_index])
        valid = int((row == score).sum()) == 1
        set_match(tmdb_episode, EpisodeMatch(score, episodes[episode_index], valid))
    for episode, column in zip(episodes, scores.T, strict=True):
        tmdb_index = int(column.argmax())
        score = float(column[tmdb_index])
        valid = int((column == score).sum()) == 1
        set_match(episode, EpisodeMatch(score, tmdb_episodes[tmdb_index], valid))


# TODO: Validate
def episode_name(episode: EpisodeRecord) -> str:
    return re.sub(
        r"\((?:sub|dub)\)",
        "",
        episode.name or "",
        flags=re.IGNORECASE,
    ).strip()


# TODO: Validate
def episode_description(episode: EpisodeRecord) -> str:
    return (episode.description or "").strip()


# TODO: Validate
def exact_key(text: str) -> str:
    return text.casefold()


# TODO: Validate
def fuzzy_key(text: str) -> str:
    without_the = re.sub(r"\bthe\b", "", text.casefold())
    return re.sub(r"[^a-z0-9]", "", without_the)


# TODO: Validate
def episode_name_key(episode: EpisodeRecord) -> str:
    return exact_key(episode_name(episode))


# TODO: Validate
def fuzzy_episode_name_key(episode: EpisodeRecord) -> str:
    return fuzzy_key(episode_name(episode))


# TODO: Validate
def episode_description_key(episode: EpisodeRecord) -> str:
    return exact_key(episode_description(episode))


# TODO: Validate
def fuzzy_episode_description_key(episode: EpisodeRecord) -> str:
    return fuzzy_key(episode_description(episode))


# TODO: Validate
def episodes_by_key(
    episodes: list[EpisodeRecord],
    key_of: Callable[[EpisodeRecord], str],
) -> defaultdict[str, list[EpisodeRecord]]:
    grouped: defaultdict[str, list[EpisodeRecord]] = defaultdict(list)
    for episode in episodes:
        if episode.linked_episode is not None:
            continue
        key = key_of(episode)
        if key:
            grouped[key].append(episode)
    return grouped


# TODO: Validate
def season_episode_number(episode: EpisodeRecord) -> tuple[int, ...] | None:
    if episode.season_number is None or episode.episode_number is None:
        return None
    return (episode.season_number, episode.episode_number)


# TODO: Validate
def absolute_episode_number(episode: EpisodeRecord) -> tuple[int, ...] | None:
    if episode.absolute_number is None:
        return None
    return (episode.absolute_number,)


# TODO: Validate
def same_number(episode: EpisodeRecord, tmdb_episode: EpisodeRecord) -> bool:
    numbered = season_episode_number(episode)
    if numbered is not None and numbered == season_episode_number(tmdb_episode):
        return True
    absolute = absolute_episode_number(episode)
    return absolute is not None and absolute == absolute_episode_number(tmdb_episode)


# TODO: Validate
def set_absolute_numbers(episodes: list[EpisodeRecord]) -> None:
    numbers = absolute_numbers(
        [
            (episode.model.id, episode.season_number, episode.episode_number)
            for episode in episodes
        ],
    )
    for episode in episodes:
        episode.absolute_number = numbers.get(episode.model.id)


# TODO: Validate
def episodes_by_number(
    episodes: list[EpisodeRecord],
    number_of: Callable[[EpisodeRecord], tuple[int, ...] | None],
) -> defaultdict[tuple[int, ...], list[EpisodeRecord]]:
    grouped: defaultdict[tuple[int, ...], list[EpisodeRecord]] = defaultdict(list)
    for episode in episodes:
        if episode.linked_episode is not None:
            continue
        number = number_of(episode)
        if number is not None:
            grouped[number].append(episode)
    return grouped


# TODO: Validate
class EpisodeLinkerV2:
    # TODO: Validate
    def __init__(self, session: Session, linked_title: Title) -> None:
        self.session = session
        self.linked_title = linked_title
        self.episodes = [
            episode_record(episode, season)
            for season in linked_title.active_children
            for episode in season.active_children
        ]
        self.tmdb_episodes = [
            episode_record(episode, season)
            for tmdb_title in linked_title.tmdb_titles
            for season in tmdb_title.active_children
            for episode in season.active_children
        ]
        set_absolute_numbers(self.episodes)
        set_absolute_numbers(self.tmdb_episodes)

    # TODO: Validate
    def link_titles(self) -> None:
        # Link identical titles first because it is fast and can reduce the number of
        # episodes for the slower more complex matching methods.
        self._link_matching_keys(episode_name_key, "Exact name", shared=True)
        self._link_matching_keys(fuzzy_episode_name_key, "Fuzzy name")
        self._link_matching_keys(episode_description_key, "Exact description")
        self._link_matching_keys(fuzzy_episode_description_key, "Fuzzy description")
        self.score_matches(
            episode_name,
            set_tfidf_name_match,
            set_embedding_name_match,
        )
        self.score_matches(
            episode_description,
            set_tfidf_description_match,
            set_embedding_description_match,
        )
        self._link_two_way_number_matches(embedding_name_match, "Embedding name")
        self._link_two_way_number_matches(tfidf_name_match, "TF-IDF name")
        self._link_two_way_number_matches(
            tfidf_description_match,
            "Embedding description",
        )
        self._link_two_way_number_matches(
            embedding_description_match,
            "TF-IDF description",
        )
        self._link_agreed_high_score_matches()
        self._link_perfect_two_way_matches()
        self.save_links()

    # TODO: Validate
    def _link_matching_keys(
        self,
        key_of: Callable[[EpisodeRecord], str],
        label: str,
        *,
        shared: bool = False,
    ) -> None:
        tmdb_episodes_by_key = episodes_by_key(self.tmdb_episodes, key_of)
        for key, episodes in episodes_by_key(self.episodes, key_of).items():
            tmdb_episodes = tmdb_episodes_by_key[key]
            if not tmdb_episodes:
                continue
            if len(tmdb_episodes) == 1 and (shared or len(episodes) == 1):
                for episode in episodes:
                    self.link(episode, tmdb_episodes[0], f"Automatic: {label} match")
                continue
            self._link_matching_keys_by_number(episodes, tmdb_episodes, label)

    # TODO: Validate
    def _link_matching_keys_by_number(
        self,
        episodes: list[EpisodeRecord],
        tmdb_episodes: list[EpisodeRecord],
        label: str,
    ) -> None:
        self._link_unique_numbers(
            episodes,
            tmdb_episodes,
            season_episode_number,
            f"Automatic: {label} and episode number match",
        )
        self._link_unique_numbers(
            episodes,
            tmdb_episodes,
            absolute_episode_number,
            f"Automatic: {label} and absolute number match",
        )

    # TODO: Validate
    def _link_unique_numbers(
        self,
        episodes: list[EpisodeRecord],
        tmdb_episodes: list[EpisodeRecord],
        number_of: Callable[[EpisodeRecord], tuple[int, ...] | None],
        note: str,
    ) -> None:
        numbered_tmdb_episodes = episodes_by_number(tmdb_episodes, number_of)
        for number, numbered_episodes in episodes_by_number(
            episodes,
            number_of,
        ).items():
            candidates = numbered_tmdb_episodes[number]
            if len(numbered_episodes) != 1 or len(candidates) != 1:
                continue
            if candidates[0].linked_episode is not None:
                continue
            if numbered_episodes[0].linked_episode is not None:
                continue
            self.link(numbered_episodes[0], candidates[0], note)

    # TODO: Validate
    def save_links(self) -> None:
        for episode in self.episodes:
            tmdb_episode = episode.linked_episode
            if tmdb_episode is None:
                continue
            if episode.model.tmdb_episode_validated_at is not None:
                continue
            if episode.model.tmdb_episode_links:
                continue
            link = EpisodeTmdbEpisode(
                episode_id=episode.model.id,
                tmdb_episode_id=tmdb_episode.model.id,
                note=episode.link_note,
            )
            link.episode = episode.model
            link.tmdb_episode = tmdb_episode.model
            episode.model.tmdb_episode_links.append(link)
            self.session.add(link)

    # TODO: Validate
    def two_way_matches(
        self,
        episode: EpisodeRecord,
        *,
        perfect_only: bool = False,
    ) -> list[EpisodeRecord]:
        matches: list[EpisodeRecord] = []
        for index, (_label, best) in enumerate(match_categories(episode)):
            if best is None or not best.valid:
                continue
            if perfect_only and round(best.score, 6) < 1:
                continue
            mutual = match_categories(best.episode)[index][1]
            if mutual is None or not mutual.valid or mutual.episode is not episode:
                continue
            if best.episode not in matches:
                matches.append(best.episode)
        return matches

    # TODO: Validate
    def _link_two_way_number_matches(
        self,
        match_of: Callable[[EpisodeRecord], EpisodeMatch | None],
        label: str,
    ) -> None:
        for episode in self.episodes:
            if episode.linked_episode is not None:
                continue
            match = match_of(episode)
            if match is None or not match.valid or match.score < 0.8:  # noqa: PLR2004
                continue
            tmdb_episode = match.episode
            if tmdb_episode.linked_episode is not None:
                continue
            if not same_number(episode, tmdb_episode):
                continue
            mutual = match_of(tmdb_episode)
            if mutual is None or not mutual.valid or mutual.episode is not episode:
                continue
            if self._agreed_match(episode, 0.8) is not tmdb_episode:
                continue
            self.link(
                episode,
                tmdb_episode,
                f"Automatic: {label} ({round(match.score * 100)}%) two-way match "
                "with episode number",
            )

    # TODO: Validate
    def _link_agreed_high_score_matches(self) -> None:
        for episode in self.episodes:
            if episode.linked_episode is not None:
                continue
            tmdb_episode = self._agreed_match(episode, 0.9)
            if tmdb_episode is None or tmdb_episode.linked_episode is not None:
                continue
            self.link(
                episode,
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with a high score"),
            )

    # TODO: Validate
    def _agreed_match(
        self,
        episode: EpisodeRecord,
        minimum_score: float,
    ) -> EpisodeRecord | None:
        agreed: EpisodeRecord | None = None
        for index, (_label, best) in enumerate(match_categories(episode)):
            if best is None or best.score < minimum_score:
                continue
            if not best.valid:
                return None
            mutual = match_categories(best.episode)[index][1]
            if mutual is None or not mutual.valid or mutual.episode is not episode:
                return None
            if agreed is not None and agreed is not best.episode:
                return None
            agreed = best.episode
        return agreed

    # TODO: Validate
    def _link_perfect_two_way_matches(self) -> None:
        for episode in self.episodes:
            if episode.linked_episode is not None:
                continue
            matches = self.two_way_matches(episode, perfect_only=True)
            if len(matches) != 1:
                continue
            tmdb_episode = matches[0]
            if tmdb_episode.linked_episode is not None:
                continue
            if self.two_way_matches(tmdb_episode, perfect_only=True) != [episode]:
                continue
            self.link(
                episode,
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with a perfect score"),
            )

    # TODO: Validate
    def link(
        self,
        episode: EpisodeRecord,
        tmdb_episode: EpisodeRecord,
        note: str,
    ) -> None:
        episode.linked_episode = tmdb_episode
        episode.link_note = note
        tmdb_episode.linked_episode = episode
        tmdb_episode.link_note = note

    # TODO: Validate
    def score_matches(
        self,
        text_of: Callable[[EpisodeRecord], str],
        set_tfidf_match: Callable[[EpisodeRecord, EpisodeMatch], None],
        set_embedding_match: Callable[[EpisodeRecord, EpisodeMatch], None],
    ) -> None:
        episodes = [
            episode
            for episode in self.episodes
            if episode.linked_episode is None and text_of(episode)
        ]
        tmdb_episodes = [
            tmdb_episode
            for tmdb_episode in self.tmdb_episodes
            if tmdb_episode.linked_episode is None and text_of(tmdb_episode)
        ]
        if not episodes or not tmdb_episodes:
            return

        matcher = TextMatcher([text_of(episode) for episode in episodes])
        tmdb_texts = [text_of(tmdb_episode) for tmdb_episode in tmdb_episodes]
        assign_best_matches(
            episodes,
            tmdb_episodes,
            matcher.tfidf_scores_of(tmdb_texts),
            set_tfidf_match,
        )
        assign_best_matches(
            episodes,
            tmdb_episodes,
            matcher.embedding_scores_of(tmdb_texts),
            set_embedding_match,
        )
