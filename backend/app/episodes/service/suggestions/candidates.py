# TODO: Validate

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlmodel import Session, col, select

from app.episodes.models import (
    Episode,
)
from app.episodes.service.numbering import absolute_numbers
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import (
    tmdb_key_clause,
)

# it, and the title above that, all as TMDB has them.
type Candidate = tuple[Episode, Season, Title]


# TODO: Validate
def candidate_absolute_numbers(candidates: list[Candidate]) -> dict[uuid.UUID, int]:
    return absolute_numbers(
        [
            (episode.id, season.season_number, episode.episode_number)
            for episode, season, _title in candidates
        ],
    )


# TODO: Validate
def candidates_by_title(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> dict[uuid.UUID, list[Candidate]]:
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
    candidates: dict[uuid.UUID, list[Candidate]] = defaultdict(list)
    for episode, season, title in session.exec(statement).all():
        candidates[title.id].append((episode, season, title))
    return candidates


# TODO: Validate
def candidates_from_titles(
    session: Session,
    titles: Collection[Title],
) -> tuple[dict[uuid.UUID, list[Candidate]], dict[uuid.UUID, dict[uuid.UUID, int]]]:
    """Return the TMDB episodes each listing can be matched against, and their count.

    Every title a listing is linked to contributes its episodes, since a listing
    that mixes titles has episodes of each of them and nothing but the match says
    which episode is which. Each title is counted through on its own, so an
    episode's place in a title is where that title puts it rather than where the
    two of them run together would.
    """
    by_title = candidates_by_title(
        session,
        {tmdb_title_id for title in titles for tmdb_title_id in title.tmdb_title_ids},
    )
    candidates: dict[uuid.UUID, list[Candidate]] = {}
    numbers: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    for title in titles:
        grouped = [
            by_title.get(tmdb_title_id, []) for tmdb_title_id in title.tmdb_title_ids
        ]
        candidates[title.id] = [candidate for group in grouped for candidate in group]
        numbers[title.id] = {
            candidate_id: number
            for group in grouped
            for candidate_id, number in candidate_absolute_numbers(group).items()
        }
    return candidates, numbers
