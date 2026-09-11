# TODO: Validate
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.episodes.models import EpisodeTmdbEpisode
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
    linked_episode: EpisodeRecord | None = None
    link_note: str | None = None
    blended_name_match: EpisodeMatch | None = None
    embedding_name_match: EpisodeMatch | None = None
    blended_description_match: EpisodeMatch | None = None
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
        ("Blended name", episode.blended_name_match),
        ("Embedding name", episode.embedding_name_match),
        ("Blended description", episode.blended_description_match),
        ("Embedding description", episode.embedding_description_match),
    )


# TODO: Validate
def set_blended_name_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.blended_name_match = match


# TODO: Validate
def set_embedding_name_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.embedding_name_match = match


# TODO: Validate
def set_blended_description_match(episode: EpisodeRecord, match: EpisodeMatch) -> None:
    episode.blended_description_match = match


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
    return (episode.name or "").strip()


# TODO: Validate
def episode_description(episode: EpisodeRecord) -> str:
    return (episode.description or "").strip()


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

    # TODO: Validate
    def link_titles(self) -> None:
        # Link identical titles first because it is fast and can reduce the number of
        # episodes for the slower more complex matching methods.
        self.link_identical_titles()
        self.score_matches(
            episode_name,
            set_blended_name_match,
            set_embedding_name_match,
        )
        self.score_matches(
            episode_description,
            set_blended_description_match,
            set_embedding_description_match,
        )
        self._link_two_way_matches_with_episode_number()
        self._link_perfect_two_way_matches()
        self.save_links()

    # TODO: Validate
    def link_identical_titles(self) -> None:
        tmdb_episodes_by_name: defaultdict[str, list[EpisodeRecord]] = defaultdict(list)
        for tmdb_episode in self.tmdb_episodes:
            name = episode_name(tmdb_episode).casefold()
            if name:
                tmdb_episodes_by_name[name].append(tmdb_episode)

        episodes_by_name: defaultdict[str, list[EpisodeRecord]] = defaultdict(list)
        for episode in self.episodes:
            name = episode_name(episode).casefold()
            if name:
                episodes_by_name[name].append(episode)

        for name, episodes in episodes_by_name.items():
            tmdb_episodes = tmdb_episodes_by_name[name]
            if len(episodes) != 1 or len(tmdb_episodes) != 1:
                continue
            self.link(episodes[0], tmdb_episodes[0], "Automatic: Exact name match")

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
    def _link_two_way_matches_with_episode_number(self) -> None:
        for episode in self.episodes:
            if episode.linked_episode is not None:
                continue
            if episode.episode_number is None or episode.season_number is None:
                continue
            matches = self.two_way_matches(episode)
            if len(matches) != 1:
                continue
            tmdb_episode = matches[0]
            if tmdb_episode.linked_episode is not None:
                continue
            if tmdb_episode.episode_number != episode.episode_number:
                continue
            if tmdb_episode.season_number != episode.season_number:
                continue
            self.link(
                episode,
                tmdb_episode,
                two_way_note(episode, tmdb_episode, "with episode number"),
            )

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
        set_blended_match: Callable[[EpisodeRecord, EpisodeMatch], None],
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
        blended_scores, embedding_scores = matcher.blended_and_embedding_scores_of(
            tmdb_texts,
        )
        assign_best_matches(episodes, tmdb_episodes, blended_scores, set_blended_match)
        assign_best_matches(
            episodes,
            tmdb_episodes,
            embedding_scores,
            set_embedding_match,
        )
