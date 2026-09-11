# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

import uuid
from collections import defaultdict
from collections.abc import Collection, Sequence

from sqlalchemy import nullslast
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, func, select

from app.episodes.models import (
    Episode,
)
from app.episodes.name_matching import (
    is_only_numbered_name,
    is_untitled_name,
    similarity,
)
from app.episodes.schemas import (
    TmdbEpisodeChoice,
)
from app.episodes.service.records import _record_fields
from app.episodes.text_matching import TextMatcher
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import (
    tmdb_key_clause,
)

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")


# What an `Episode` can be pointed at: the episode itself, the season holding
# it, and the title above that, all as TMDB has them.
type _Candidate = tuple[Episode, Season, Title]


type Numbering = tuple[uuid.UUID, int | None, int | None]


# TODO: Validate
def _order(
    season_number: int | None,
    episode_number: int | None,
) -> tuple[float, float]:
    return (
        _UNNUMBERED if season_number is None else season_number,
        _UNNUMBERED if episode_number is None else episode_number,
    )


# TODO: Validate
def absolute_numbers(numberings: Sequence[Numbering]) -> dict[uuid.UUID, int]:
    """Count every episode of one title from its first, and return that count by id.

    A website that numbers a title straight through names an episode by how far
    into the title it is rather than by how far into its own season, which is
    what makes the same episode `S3E2` on one site and `27` on another. Specials
    are outside the count, since a title's own episodes are what the count runs
    over, so they are left with no number rather than given one.
    """
    ordered = sorted(
        numberings,
        key=lambda numbering: (
            *_order(numbering[1], numbering[2]),
            numbering[0].bytes,
        ),
    )
    numbers: dict[uuid.UUID, int] = {}
    for record_id, season_number, _episode_number in ordered:
        if not season_number:
            continue
        numbers[record_id] = len(numbers) + 1
    return numbers


# TODO: Validate
def _score(
    episode: Episode,
    season: Season,
    candidate: _Candidate,
) -> tuple[float, int]:
    candidate_episode, candidate_season, _title = candidate
    numbering_matches = int(
        season.season_number is not None
        and episode.episode_number is not None
        and candidate_season.season_number == season.season_number
        and candidate_episode.episode_number == episode.episode_number,
    )
    return similarity(episode.name, candidate_episode.name), numbering_matches


# TODO: Validate
def _candidate_absolute_numbers(candidates: list[_Candidate]) -> dict[uuid.UUID, int]:
    return absolute_numbers(
        [
            (episode.id, season.season_number, episode.episode_number)
            for episode, season, _title in candidates
        ],
    )


# TODO: Validate
def _choice(
    candidate: _Candidate,
    absolute_numbers: dict[uuid.UUID, int],
    similarity: float,
) -> TmdbEpisodeChoice | None:
    episode, season, title = candidate
    return TmdbEpisodeChoice(
        **_record_fields(episode, season, title),
        absolute_number=absolute_numbers.get(episode.id),
        similarity=similarity,
    )


# TODO: Validate
def _best_match(
    episode: Episode,
    season: Season,
    candidates: list[_Candidate],
    absolute_numbers: dict[uuid.UUID, int],
) -> TmdbEpisodeChoice | None:
    """Return the TMDB episode closest to `episode`, or `None` when none is close.

    A candidate is scored on how much of its name it shares with the episode's,
    and an episode filed under the same season and episode number wins a tie. A
    candidate that shares no name and no numbering is not a guess worth showing,
    so nothing is returned rather than an arbitrary episode of the title.
    """
    scored = [
        (_score(episode, season, candidate), candidate) for candidate in candidates
    ]
    if not scored:
        return None

    (similarity, numbering_matches), candidate = max(scored, key=lambda pair: pair[0])
    if similarity == 0.0 and not numbering_matches:
        return None

    return _choice(candidate, absolute_numbers, similarity)


# TODO: Validate
def _episode_text(episode: Episode, *, titles: bool) -> str:
    if not titles:
        return (episode.description or "").strip()
    name = (episode.name or "").strip()
    if not name or is_untitled_name(name) or is_only_numbered_name(name):
        return ""
    return name


# TODO: Validate
def _text_matchers(
    candidates: dict[uuid.UUID, list[_Candidate]],
    *,
    titles: bool,
) -> dict[uuid.UUID, tuple[list[_Candidate], TextMatcher]]:
    matchers: dict[uuid.UUID, tuple[list[_Candidate], TextMatcher]] = {}
    for title_id, title_candidates in candidates.items():
        written = [
            candidate
            for candidate in title_candidates
            if _episode_text(candidate[0], titles=titles)
        ]
        if written:
            matchers[title_id] = (
                written,
                TextMatcher(
                    [
                        _episode_text(candidate[0], titles=titles)
                        for candidate in written
                    ],
                ),
            )
    return matchers


# TODO: Validate
def _text_matches(
    episode: Episode,
    matcher: tuple[list[_Candidate], TextMatcher] | None,
    absolute_numbers: dict[uuid.UUID, int],
    *,
    titles: bool,
    blended: bool,
) -> list[TmdbEpisodeChoice]:
    text = _episode_text(episode, titles=titles)
    if matcher is None or not text:
        return []

    written_candidates, text_matcher = matcher
    scores = (
        text_matcher.blended_scores(text)
        if blended
        else text_matcher.embedding_scores(text)
    )
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    choices = [
        _choice(written_candidates[index], absolute_numbers, scores[index])
        for index in ranked[:2]
        if scores[index] > 0.0
    ]
    return [choice for choice in choices if choice is not None]


# TODO: Validate
def _season_and_episode_match(
    episode: Episode,
    season: Season,
    candidates: list[_Candidate],
    absolute_numbers: dict[uuid.UUID, int],
) -> TmdbEpisodeChoice | None:
    for candidate in candidates:
        candidate_episode, candidate_season, _title = candidate
        if (
            season.season_number is not None
            and episode.episode_number is not None
            and candidate_season.season_number == season.season_number
            and candidate_episode.episode_number == episode.episode_number
        ):
            return _choice(
                candidate,
                absolute_numbers,
                similarity(episode.name, candidate_episode.name),
            )
    return None


# TODO: Validate
def _absolute_number_match(
    episode: Episode,
    candidates: list[_Candidate],
    absolute_numbers: dict[uuid.UUID, int],
    own_absolute: int | None,
) -> TmdbEpisodeChoice | None:
    if own_absolute is None:
        return None
    for candidate in candidates:
        candidate_episode = candidate[0]
        candidate_absolute = absolute_numbers.get(candidate_episode.id)
        if own_absolute == candidate_absolute:
            return _choice(
                candidate,
                absolute_numbers,
                similarity(episode.name, candidate_episode.name),
            )
    return None


# TODO: Validate
def _episode_number_absolute_match(
    episode: Episode,
    candidates: list[_Candidate],
    absolute_numbers: dict[uuid.UUID, int],
) -> TmdbEpisodeChoice | None:
    if episode.episode_number is None:
        return None
    for candidate in candidates:
        candidate_episode = candidate[0]
        if episode.episode_number == absolute_numbers.get(candidate_episode.id):
            return _choice(
                candidate,
                absolute_numbers,
                similarity(episode.name, candidate_episode.name),
            )
    return None


# TODO: Validate
def _candidates_by_title(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> dict[uuid.UUID, list[_Candidate]]:
    """Return every TMDB episode of each linked title, keyed by the title.

    A title's episodes are read once for the whole page rather than once per
    episode, since every episode of the same title is compared against the same
    list.
    """
    if not tmdb_title_ids:
        return {}

    statement = (
        select(Episode, Season, Title)
        .join(
            Season,
            onclause=col(Episode.season_id) == Season.id,
        )
        .join(
            Title,
            onclause=col(Season.title_id) == Title.id,
        )
        .where(
            is_not_linked(Episode),
            is_not_linked(Title),
            col(Title.id).in_(tmdb_title_ids),
            tmdb_key_clause(col(Episode.key)),
        )
    )
    candidates: dict[uuid.UUID, list[_Candidate]] = defaultdict(list)
    for episode, season, title in session.exec(statement).all():
        candidates[title.id].append((episode, season, title))
    return candidates


# TODO: Validate
def _candidates_from_titles(
    session: Session,
    titles: Collection[Title],
) -> tuple[dict[uuid.UUID, list[_Candidate]], dict[uuid.UUID, dict[uuid.UUID, int]]]:
    """Return the TMDB episodes each listing can be matched against, and their count.

    Every title a listing is linked to contributes its episodes, since a listing
    that mixes titles has episodes of each of them and nothing but the match says
    which episode is which. Each title is counted through on its own, so an
    episode's place in a title is where that title puts it rather than where the
    two of them run together would.
    """
    by_title = _candidates_by_title(
        session,
        {
            tmdb_title_id
            for title in titles
            for tmdb_title_id in title.tmdb_title_ids
        },
    )
    candidates: dict[uuid.UUID, list[_Candidate]] = {}
    numbers: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    for title in titles:
        grouped = [
            by_title.get(tmdb_title_id, [])
            for tmdb_title_id in title.tmdb_title_ids
        ]
        candidates[title.id] = [candidate for group in grouped for candidate in group]
        numbers[title.id] = {
            candidate_id: number
            for group in grouped
            for candidate_id, number in _candidate_absolute_numbers(group).items()
        }
    return candidates, numbers


# TODO: Validate
def _counted_episodes() -> ColumnElement[bool]:
    """Which of a title's episodes the count runs over.

    A season nothing numbered and season zero are both outside it, so a special
    is left with no number rather than given one and does not push the episode
    after it along.
    """
    return and_(
        col(Episode.deleted_at).is_(None),
        col(Season.deleted_at).is_(None),
        col(Season.season_number).is_not(None),
        col(Season.season_number) != 0,
    )


# TODO: Validate
def _absolute_number_column() -> ColumnElement[int]:
    """Count each title through from its first episode.

    `nullslast` is what Postgres does with an ascending sort anyway, said outright
    because it is what stands in for `_UNNUMBERED`, and the id is what settles two
    episodes a website gave the very same numbering.
    """
    return func.row_number().over(
        partition_by=col(Season.title_id),
        order_by=(
            col(Season.season_number),
            nullslast(col(Episode.episode_number)),
            col(Episode.id),
        ),
    )


# TODO: Validate
def absolute_numbers_of(
    session: Session,
    title_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Count every episode of each title, and return that count by episode id.

    The whole title is counted rather than only the episodes being listed, since an
    episode's place in a title is decided by how many come before it, which the
    ones left over from a name match say nothing about. Nothing says which rows are
    canonical, so a website's own title and a canonical title are both counted the
    way the title they are counts.
    """
    if not title_ids:
        return {}

    statement = (
        select(Episode.id, _absolute_number_column())
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(col(Season.title_id).in_(title_ids), _counted_episodes())
    )
    return dict(session.exec(statement).all())
