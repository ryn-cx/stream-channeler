# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING

from app.episodes.service.linking.details import (
    CombinedMatch,
    EpisodeDetails,
    EpisodeMatch,
    MatchKind,
)
from app.episodes.service.linking.numbers import (
    same_number,
    season_and_episode_number,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy  # noqa: ICN001


# TODO: Validate
def agreed_matches(
    episode: EpisodeDetails,
    tmdb_episode: EpisodeDetails,
) -> list[tuple[MatchKind, EpisodeMatch]]:
    """Return the ways of scoring where both episodes picked each other as their best
    match.
    """
    agreed: list[tuple[MatchKind, EpisodeMatch]] = []
    for kind in MatchKind:
        best = episode.matches.get(kind)
        if best is None or not best.valid or best.episode is not tmdb_episode:
            continue
        mutual = tmdb_episode.matches.get(kind)
        if mutual is None or not mutual.valid or mutual.episode is not episode:
            continue
        agreed.append((kind, best))
    return agreed


# TODO: Validate
def two_way_note(
    episode: EpisodeDetails,
    tmdb_episode: EpisodeDetails,
    reason: str,
) -> str:
    """Write the note saying the two episodes picked each other, and how well they
    scored.
    """
    labels = [
        f"{kind} ({round(match.score * 100)}%)"
        for kind, match in agreed_matches(episode, tmdb_episode)
    ]
    return f"Automatic: {', '.join(labels)} two-way match {reason}"


# TODO: Validate
def same_numbered(episodes: Sequence[EpisodeDetails]) -> bool:
    numbers = {season_and_episode_number(episode) for episode in episodes}
    return len(numbers) == 1 and None not in numbers


# TODO: Validate
def best_match(
    scores: numpy.ndarray,
    episodes: Sequence[EpisodeDetails],
    *,
    shareable: bool = False,
) -> EpisodeMatch:
    score = float(scores.max())
    winning = scores == scores.max()
    winners = [
        episode for episode, won in zip(episodes, winning, strict=True) if bool(won)
    ]
    losing_scores = scores[~winning]
    runner_up = float(losing_scores.max()) if losing_scores.size else 0.0
    valid = len(winners) == 1 or (shareable and same_numbered(winners))
    return EpisodeMatch(score, winners, valid, runner_up)


# TODO: Validate
def combined_match(
    episode: EpisodeDetails,
    kinds: Sequence[MatchKind],
) -> CombinedMatch | None:
    scored = [
        (kind, match)
        for kind in kinds
        if (match := episode.matches.get(kind)) is not None
    ]
    if not scored:
        return None
    best = max(scored, key=lambda kind_match: kind_match[1].score)[1]
    if not best.valid:
        return None
    runner_up = max(
        match.runner_up if match.picked(best.episode) else match.score
        for _, match in scored
    )
    kind_scores = tuple(
        (kind, match.score)
        for kind, match in scored
        if match.picked(best.episode) and match.valid
    )
    return CombinedMatch(best.score, best.episodes, runner_up, kind_scores)


# TODO: Validate
def combined_two_way(
    episode: EpisodeDetails,
    kinds: Sequence[MatchKind],
) -> tuple[CombinedMatch, CombinedMatch] | None:
    combined = combined_match(episode, kinds)
    if combined is None:
        return None
    mutual = combined_match(combined.episode, kinds)
    if mutual is None or not mutual.picked(episode):
        return None
    if any(not mutual.picked(linked) for linked in combined.episode.linked_episodes):
        return None
    return combined, mutual


# TODO: Validate
def combined_note(combined: CombinedMatch, reason: str) -> str:
    labels = [f"{kind} ({round(score * 100)}%)" for kind, score in combined.kind_scores]
    return f"Automatic: {', '.join(labels)} {reason}"


# TODO: Validate
def required_gap(score: float) -> float:
    return max(0.05, (1.0 - score) / 2)


# TODO: Validate
def clear_score(score: float, runner_up: float, *, floor: bool = True) -> bool:
    if floor and score < 0.8:  # noqa: PLR2004
        return False
    return score - runner_up >= required_gap(score)


# TODO: Validate
def clear_two_way_match(
    episode: EpisodeDetails,
    kinds: Sequence[MatchKind],
) -> CombinedMatch | None:
    two_way = combined_two_way(episode, kinds)
    if two_way is None:
        return None
    combined = two_way[0]
    floor = not same_number(episode, combined.episode)
    for kind, score in combined.kind_scores:
        if clear_score(score, episode.matches[kind].runner_up, floor=floor):
            return combined
    return None


# TODO: Validate
def clear_match(match: CombinedMatch) -> bool:
    """Say whether the match scored high with nothing else anywhere near it, which is
    good enough to go on by itself.
    """
    return clear_score(match.score, match.runner_up)


# TODO: Validate
def _part_match[DetailsT: EpisodeDetails](
    scores: numpy.ndarray,
    row: int,
    candidates: list[DetailsT],
) -> DetailsT | None:
    part_scores = scores[row]
    column = int(part_scores.argmax())
    score = float(part_scores[column])
    winning = part_scores == score
    if int(winning.sum()) != 1:
        return None
    losing = part_scores[~winning]
    runner_up = float(losing.max()) if losing.size else 0.0
    if not clear_score(score, runner_up):
        return None
    return candidates[column]


# TODO: Validate
def agreed_part_match[DetailsT: EpisodeDetails](
    tfidf: numpy.ndarray,
    embedding: numpy.ndarray,
    row: int,
    candidates: list[DetailsT],
) -> DetailsT | None:
    """Return the episode the two scorers point at for one part of a combined name,
    so long as they do not disagree. Either both picked it, or one picked it and the
    other picked nobody at all.
    """
    tfidf_pick = _part_match(tfidf, row, candidates)
    embedding_pick = _part_match(embedding, row, candidates)
    if tfidf_pick is None:
        return embedding_pick
    if embedding_pick is None:
        return tfidf_pick
    return tfidf_pick if tfidf_pick is embedding_pick else None


# TODO: Validate
def scored_part_matches[DetailsT: EpisodeDetails](
    tfidf: numpy.ndarray,
    embedding: numpy.ndarray,
    rows: range,
    candidates: list[DetailsT],
) -> list[DetailsT] | None:
    """Find the episode each part of a combined name was scored onto, or nothing when
    any part does not land on one episode of its own that still needs a link.
    """
    matches: list[DetailsT] = []
    for row in rows:
        match = agreed_part_match(tfidf, embedding, row, candidates)
        if match is None or match.linked_episodes:
            return None
        if any(match is found for found in matches):
            return None
        matches.append(match)
    return matches


# TODO: Validate
def assign_best_matches(
    episodes: Sequence[EpisodeDetails],
    tmdb_episodes: Sequence[EpisodeDetails],
    scores: numpy.ndarray,
    kind: MatchKind,
) -> None:
    """Give every episode on both sides its best match out of the score grid, and mark
    that match invalid when something else tied with it.
    """
    for tmdb_episode, row in zip(tmdb_episodes, scores, strict=True):
        tmdb_episode.matches[kind] = best_match(row, episodes, shareable=True)
    for episode, column in zip(episodes, scores.T, strict=True):
        episode.matches[kind] = best_match(column, tmdb_episodes)
