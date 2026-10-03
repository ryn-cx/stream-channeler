# TODO: Validate

import uuid

from app.episodes.models import (
    Episode,
)
from app.episodes.schemas import (
    TmdbEpisodeChoice,
)
from app.episodes.service.names.forms import (
    get_normalized_episode_name,
)
from app.episodes.service.names.matching import (
    name_parts,
    similarity,
)
from app.episodes.service.names.scored_text import (
    description_for_scoring,
    name_for_scoring,
)
from app.episodes.service.names.vectors import TextMatcher
from app.episodes.service.records import record_fields
from app.episodes.service.suggestions.candidates import Candidate
from app.seasons.models import Season

type _Matcher = tuple[list[Candidate], TextMatcher, list[int]]


# TODO: Validate
def episode_choice(
    candidate: Candidate,
    absolute_numbers: dict[uuid.UUID, int],
    similarity: float,
) -> TmdbEpisodeChoice:
    episode, season, title = candidate
    return TmdbEpisodeChoice(
        **record_fields(episode, season, title),
        absolute_number=absolute_numbers.get(episode.id),
        similarity=similarity,
    )


# TODO: Validate
def _name_similarity(name: str | None, other_name: str | None) -> float:
    return max(
        (
            similarity(part, other_part)
            for part in name_parts(name)
            for other_part in name_parts(other_name)
        ),
        default=0.0,
    )


# TODO: Validate
def episode_text(episode: Episode, title_name: str | None, *, titles: bool) -> str:
    if not titles:
        return description_for_scoring(episode.description)
    return name_for_scoring(episode.name, title_name)


# TODO: Validate
def _episode_texts(
    episode: Episode,
    title_name: str | None,
    *,
    titles: bool,
) -> list[str]:
    text = episode_text(episode, title_name, titles=titles)
    if not text:
        return []
    if not titles:
        return [text]
    return list(name_parts(text))


# TODO: Validate
def text_matchers(
    candidates: dict[uuid.UUID, list[Candidate]],
    *,
    titles: bool,
) -> dict[uuid.UUID, _Matcher]:
    matchers: dict[uuid.UUID, _Matcher] = {}
    for title_id, title_candidates in candidates.items():
        written: list[Candidate] = []
        documents: list[str] = []
        candidate_positions: list[int] = []
        for candidate in title_candidates:
            texts = _episode_texts(candidate[0], candidate[2].name, titles=titles)
            if not texts:
                continue
            position = len(written)
            written.append(candidate)
            documents.extend(texts)
            candidate_positions.extend([position] * len(texts))
        if written:
            matchers[title_id] = (written, TextMatcher(documents), candidate_positions)
    return matchers


# TODO: Validate
def text_matches(  # noqa: PLR0913
    episode: Episode,
    title_name: str | None,
    matcher: _Matcher | None,
    absolute_numbers: dict[uuid.UUID, int],
    *,
    titles: bool,
    tfidf: bool,
) -> list[TmdbEpisodeChoice]:
    texts = _episode_texts(episode, title_name, titles=titles)
    if matcher is None or not texts:
        return []

    written_candidates, text_matcher, candidate_positions = matcher
    document_scores = (
        text_matcher.tfidf_scores_of(texts)
        if tfidf
        else text_matcher.embedding_scores_of(texts)
    ).max(axis=0)
    scores = [0.0] * len(written_candidates)
    for position, score in zip(
        candidate_positions,
        document_scores.tolist(),
        strict=True,
    ):
        scores[position] = max(scores[position], score)
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    top_ranked = ranked[:2]
    strong_enough = [
        index
        for index in ranked[2:]
        if scores[index] > 0.5  # noqa: PLR2004
    ]
    return [
        episode_choice(written_candidates[index], absolute_numbers, scores[index])
        for index in top_ranked + strong_enough
        if scores[index] > 0.0
    ][:5]


# TODO: Validate
def season_and_episode_match(
    episode: Episode,
    title_name: str | None,
    season: Season,
    candidates: list[Candidate],
    absolute_numbers: dict[uuid.UUID, int],
) -> TmdbEpisodeChoice | None:
    for candidate in candidates:
        candidate_episode, candidate_season, candidate_title = candidate
        if (
            season.season_number is not None
            and episode.episode_number is not None
            and candidate_season.season_number == season.season_number
            and candidate_episode.episode_number == episode.episode_number
        ):
            return episode_choice(
                candidate,
                absolute_numbers,
                _name_similarity(
                    get_normalized_episode_name(episode.name, title_name),
                    get_normalized_episode_name(
                        candidate_episode.name,
                        candidate_title.name,
                    ),
                ),
            )
    return None


# TODO: Validate
def absolute_number_match(
    episode: Episode,
    title_name: str | None,
    candidates: list[Candidate],
    absolute_numbers: dict[uuid.UUID, int],
    own_absolute: int | None,
) -> TmdbEpisodeChoice | None:
    if own_absolute is None:
        return None
    for candidate in candidates:
        candidate_episode, _season, candidate_title = candidate
        candidate_absolute = absolute_numbers.get(candidate_episode.id)
        if own_absolute == candidate_absolute:
            return episode_choice(
                candidate,
                absolute_numbers,
                _name_similarity(
                    get_normalized_episode_name(episode.name, title_name),
                    get_normalized_episode_name(
                        candidate_episode.name,
                        candidate_title.name,
                    ),
                ),
            )
    return None


# TODO: Validate
def episode_number_absolute_match(
    episode: Episode,
    title_name: str | None,
    candidates: list[Candidate],
    absolute_numbers: dict[uuid.UUID, int],
) -> TmdbEpisodeChoice | None:
    if episode.episode_number is None:
        return None
    for candidate in candidates:
        candidate_episode, _season, candidate_title = candidate
        if episode.episode_number == absolute_numbers.get(candidate_episode.id):
            return episode_choice(
                candidate,
                absolute_numbers,
                _name_similarity(
                    get_normalized_episode_name(episode.name, title_name),
                    get_normalized_episode_name(
                        candidate_episode.name,
                        candidate_title.name,
                    ),
                ),
            )
    return None
