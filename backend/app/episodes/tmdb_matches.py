# TODO: Validate
"""Episodes no TMDB record was found for, each beside the closest TMDB episode.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered
here, each paired with the TMDB episode that came closest, so the link a name
could not make can be made by hand instead.
"""

import uuid
from collections import defaultdict
from collections.abc import Collection, Sequence
from difflib import SequenceMatcher

from fastapi import HTTPException
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    not_tmdb_key_clause,
    tmdb_id_of,
    tmdb_key_clause,
)
from app.episodes.models import (
    Episode,
)
from app.episodes.schemas import (
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
)
from app.media.canonical_metadata import tmdb_episode_url
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")

# What an `Episode` can be pointed at: the episode itself, the season holding
# it, and the title above that, all as TMDB has them.
type _Candidate = tuple[Episode, Season, Show]
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
        key=lambda numbering: _order(numbering[1], numbering[2]),
    )
    numbers: dict[uuid.UUID, int] = {}
    for record_id, season_number, _episode_number in ordered:
        if not season_number:
            continue
        numbers[record_id] = len(numbers) + 1
    return numbers


# TODO: Validate
def _plaintext(name: str | None) -> str:
    if not name:
        return ""
    return "".join(character for character in name.casefold() if character.isalnum())


# TODO: Validate
def _similarity(name: str | None, other_name: str | None) -> float:
    plaintext = _plaintext(name)
    other_plaintext = _plaintext(other_name)
    if not plaintext or not other_plaintext:
        return 0.0

    ratio = SequenceMatcher(None, plaintext, other_plaintext).ratio()
    if plaintext not in other_plaintext and other_plaintext not in plaintext:
        return ratio

    # One name sitting inside the other is worth only as much of the longer name
    # as it covers. A name of a letter or two is inside almost every other name,
    # and reading as a perfect match against the whole catalogue says nothing
    # about which episode it is. Never below what the names share outright, so
    # containment can only ever help.
    shorter, longer = sorted((plaintext, other_plaintext), key=len)
    return max(ratio, len(shorter) / len(longer))


# TODO: Validate
def _score(
    episode: Episode,
    season: Season,
    candidate: _Candidate,
) -> tuple[float, int]:
    candidate_episode, candidate_season, _show = candidate
    numbering_matches = int(
        season.season_number is not None
        and episode.episode_number is not None
        and candidate_season.season_number == season.season_number
        and candidate_episode.episode_number == episode.episode_number,
    )
    return _similarity(episode.name, candidate_episode.name), numbering_matches


# TODO: Validate
def _candidate_absolute_numbers(candidates: list[_Candidate]) -> dict[uuid.UUID, int]:
    return absolute_numbers(
        [
            (episode.id, season.season_number, episode.episode_number)
            for episode, season, _show in candidates
        ],
    )


# TODO: Validate
def _choice(
    candidate: _Candidate,
    absolute_numbers: dict[uuid.UUID, int],
    similarity: float,
) -> TmdbEpisodeChoice | None:
    episode, season, show = candidate
    tmdb_episode_id = tmdb_id_of(episode.key, EPISODE_LEVEL)
    if tmdb_episode_id is None:
        return None

    return TmdbEpisodeChoice(
        tmdb_episode_id=tmdb_episode_id,
        name=episode.name,
        season_number=season.season_number,
        episode_number=episode.episode_number,
        absolute_number=absolute_numbers.get(episode.id),
        url=tmdb_episode_url(
            show.key,
            season.season_number,
            episode.episode_number,
        ),
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
def _has_tmdb_title() -> ColumnElement[bool]:
    """Whether TMDB holds any of the titles the outer `Show` is a copy of.

    Any of them rather than the one it is chiefly of, since a listing that mixes
    titles is as much a copy of the second as of the first and an episode of
    either is one there are TMDB episodes to match it against.
    """
    canonical_show = aliased(Show)
    return (
        select(ShowCanonicalShow.show_id)
        .select_from(ShowCanonicalShow)
        .join(
            canonical_show,
            onclause=col(ShowCanonicalShow.canonical_show_id) == canonical_show.id,
        )
        .where(
            is_canonical(canonical_show),
            col(ShowCanonicalShow.show_id) == col(Show.id),
            tmdb_key_clause(col(canonical_show.key)),
        )
        .correlate(Show)
        .exists()
    )


# TODO: Validate
def _unmatched_rows(
    session: Session,
    limit: int,
) -> list[tuple[Episode, Season, Show, Source]]:
    canonical_episode = aliased(Episode)
    statement = (
        select(Episode, Season, Show, Source)
        .select_from(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .join(
            canonical_episode,
            onclause=col(Episode.canonical_episode_id) == canonical_episode.id,
        )
        .where(
            Plugin.key != TMDB_PLUGIN_KEY,
            is_canonical(canonical_episode),
            # The episode is a copy of something TMDB has no record of, while one
            # of the titles above it is one TMDB does hold: that gap is exactly
            # what is left to match.
            not_tmdb_key_clause(col(canonical_episode.key)),
            _has_tmdb_title(),
            # A locked link is one a `User` has already settled, whether by
            # pointing the episode at a TMDB record or by saying there is none to
            # point it at, so it is no longer waiting on anybody.
            col(Episode.canonical_episode_locked).is_(False),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(
            col(Show.name),
            col(Season.season_number),
            col(Episode.episode_number),
        )
        .limit(limit)
    )
    return list(session.exec(statement).all())


# TODO: Validate
def _candidates_by_show(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, list[_Candidate]]:
    """Return every TMDB episode of each linked title, keyed by the title.

    A title's episodes are read once for the whole page rather than once per
    episode, since every episode of the same title is compared against the same
    list.
    """
    if not canonical_show_ids:
        return {}

    statement = (
        select(Episode, Season, Show)
        .join(
            Season,
            onclause=col(Episode.season_id) == Season.id,
        )
        .join(
            Show,
            onclause=col(Season.show_id) == Show.id,
        )
        .where(
            is_canonical(Episode),
            is_canonical(Show),
            col(Show.id).in_(canonical_show_ids),
            tmdb_key_clause(col(Episode.key)),
        )
    )
    candidates: dict[uuid.UUID, list[_Candidate]] = defaultdict(list)
    for episode, season, show in session.exec(statement).all():
        candidates[show.id].append((episode, season, show))
    return candidates


# TODO: Validate
def _candidates_for_shows(
    session: Session,
    shows: Collection[Show],
) -> tuple[dict[uuid.UUID, list[_Candidate]], dict[uuid.UUID, dict[uuid.UUID, int]]]:
    """Return the TMDB episodes each listing can be matched against, and their count.

    Every title a listing is a copy of contributes its episodes, since a listing
    that mixes titles has episodes of each of them and nothing but the match says
    which episode is which. Each title is counted through on its own, so an
    episode's place in a title is where that title puts it rather than where the
    two of them run together would.
    """
    by_title = _candidates_by_show(
        session,
        {
            canonical_show_id
            for show in shows
            for canonical_show_id in show.canonical_show_ids
        },
    )
    candidates: dict[uuid.UUID, list[_Candidate]] = {}
    numbers: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    for show in shows:
        titles = [by_title.get(title, []) for title in show.canonical_show_ids]
        candidates[show.id] = [candidate for title in titles for candidate in title]
        numbers[show.id] = {
            candidate_id: number
            for title in titles
            for candidate_id, number in _candidate_absolute_numbers(title).items()
        }
    return candidates, numbers


# TODO: Validate
def _source_absolute_numbers(
    session: Session,
    show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Count every episode of each website's own title, and return that count by id.

    The whole title is read rather than only the episodes being listed, since an
    episode's place in a title is decided by how many come before it, which the
    ones left over from a name match say nothing about.
    """
    if not show_ids:
        return {}

    statement = (
        select(Episode.id, Season.show_id, Season.season_number, Episode.episode_number)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            col(Season.show_id).in_(show_ids),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    per_show: dict[uuid.UUID, list[Numbering]] = defaultdict(list)
    for episode_id, show_id, season_number, episode_number in session.exec(
        statement,
    ).all():
        per_show[show_id].append((episode_id, season_number, episode_number))

    numbers: dict[uuid.UUID, int] = {}
    for numberings in per_show.values():
        numbers |= absolute_numbers(numberings)
    return numbers


# TODO: Validate
def list_unmatched_episodes(
    session: Session,
    limit: int,
) -> list[UnmatchedEpisodeOutput]:
    """Return the episodes that are still a copy of nothing but themselves.

    Only episodes of a title that is itself linked are listed, since a title with
    no TMDB counterpart has no episodes to be matched against and nothing to
    choose from.
    """
    rows = _unmatched_rows(session, limit)
    candidates, candidate_numbers = _candidates_for_shows(
        session,
        {show for _episode, _season, show, _source in rows},
    )
    source_numbers = _source_absolute_numbers(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    return [
        UnmatchedEpisodeOutput(
            id=episode.id,
            canonical_episode_id=episode.canonical_episode_id,
            canonical_episode_note=episode.canonical_episode_note,
            name=episode.name,
            episode_number=episode.episode_number,
            absolute_number=source_numbers.get(episode.id),
            season_id=season.id,
            season_name=season.name,
            season_number=season.season_number,
            show_id=show.id,
            show_name=show.name,
            source_id=source.id,
            source_name=source.name,
            url=episode.url,
            best_match=_best_match(
                episode,
                season,
                candidates.get(show.id, []),
                candidate_numbers.get(show.id, {}),
            ),
        )
        for episode, season, show, source in rows
    ]


# TODO: Validate
def _unlocked_rows(
    session: Session,
    limit: int,
) -> list[tuple[Episode, Season, Show, Source]]:
    """Return every episode whose TMDB link no `User` has settled.

    The episodes that were linked are kept rather than filtered out, which is
    what separates this from `_unmatched_rows`: a link made against a wrong name
    is still a link, and it is only ever spotted beside the TMDB episode it was
    made against.
    """
    statement = (
        select(Episode, Season, Show, Source)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            Plugin.key != TMDB_PLUGIN_KEY,
            col(Episode.canonical_episode_locked).is_(False),
            _has_tmdb_title(),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(
            col(Show.name),
            col(Season.season_number),
            col(Episode.episode_number),
        )
        .limit(limit)
    )
    return list(session.exec(statement).all())


# TODO: Validate
def list_unlocked_episodes(
    session: Session,
    limit: int,
) -> list[UnlockedEpisodeOutput]:
    """Return every episode whose TMDB link no `User` has settled.

    Only episodes of a title that is itself linked are listed, since a title with
    no TMDB counterpart has no episodes to be matched against.
    """
    rows = _unlocked_rows(session, limit)
    candidates, candidate_numbers = _candidates_for_shows(
        session,
        {show for _episode, _season, show, _source in rows},
    )
    source_numbers = _source_absolute_numbers(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    outputs: list[UnlockedEpisodeOutput] = []
    for episode, season, show, source in rows:
        best_match = _best_match(
            episode,
            season,
            candidates.get(show.id, []),
            candidate_numbers.get(show.id, {}),
        )
        outputs.append(
            UnlockedEpisodeOutput(
                id=episode.id,
                canonical_episode_id=episode.canonical_episode_id,
                canonical_episode_note=episode.canonical_episode_note,
                name=episode.name,
                episode_number=episode.episode_number,
                absolute_number=source_numbers.get(episode.id),
                season_id=season.id,
                season_name=season.name,
                season_number=season.season_number,
                show_id=show.id,
                show_name=show.name,
                source_id=source.id,
                source_name=source.name,
                url=episode.url,
                best_match=best_match,
                name_matches=bool(
                    best_match
                    and _plaintext(episode.name)
                    and _plaintext(episode.name) == _plaintext(best_match.name),
                ),
            ),
        )
    return outputs


# TODO: Validate
def _tmdb_ids_used_by_show(session: Session, episode: Episode) -> set[int]:
    """Return the TMDB episodes the rest of `episode`'s show already points at.

    Only the show the episode belongs to is read, since another website's copy
    of the same title has its own episodes pointing at the same TMDB ones and
    says nothing about which of them this show still has going spare. The
    episode being linked is left out so the record it already points at is not
    counted as somebody else's.
    """
    canonical_episode = aliased(Episode)
    statement = (
        select(canonical_episode.key)
        .select_from(Episode)
        .join(
            canonical_episode,
            onclause=col(Episode.canonical_episode_id) == canonical_episode.id,
        )
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(canonical_episode),
            Season.show_id == episode.season.show_id,
            col(Episode.id) != episode.id,
            tmdb_key_clause(col(canonical_episode.key)),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    return {
        tmdb_id
        for key in session.exec(statement).all()
        if (tmdb_id := tmdb_id_of(key, EPISODE_LEVEL)) is not None
    }


# TODO: Validate
def _imported_title(session: Session, tmdb_show_id: int) -> uuid.UUID:
    """Read a TMDB series in and return the title its episodes are under.

    Read in rather than looked for, since a title nothing has imported has no
    episodes stored to choose from and naming it is the asking for it.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    canonical_show = TMDB(session).import_show(tmdb_show_id)
    if canonical_show is None:
        raise HTTPException(
            status_code=400,
            detail=f"TMDB has no series with the id {tmdb_show_id}",
        )
    return canonical_show.id


# TODO: Validate
def list_tmdb_episode_choices(
    session: Session,
    episode: Episode,
    tmdb_show_id: int | None = None,
) -> list[TmdbEpisodeChoice]:
    """Return every TMDB episode of a title, in the order the title runs.

    They are ordered as the title runs rather than as TMDB returns them, so the
    one an episode is meant to be is found by counting through the title the same
    way the website that holds it does. Each carries how much of its name it
    shares with `episode`, which is the other order they are worth reading in.

    The titles are the ones the episode's show is linked to, unless another is
    named outright. TMDB files some episodes under a title of their own, so an
    episode is not always among the episodes of the titles its show is, and naming
    the title it is under is the only way to reach it.
    """
    canonical_show_ids = (
        episode.season.show.canonical_show_ids
        if tmdb_show_id is None
        else [_imported_title(session, tmdb_show_id)]
    )
    if not canonical_show_ids:
        return []
    by_title = _candidates_by_show(session, set(canonical_show_ids))
    titles = [
        by_title.get(canonical_show_id, []) for canonical_show_id in canonical_show_ids
    ]
    candidates = [candidate for title in titles for candidate in title]
    absolute_numbers = {
        candidate_id: number
        for title in titles
        for candidate_id, number in _candidate_absolute_numbers(title).items()
    }
    used_tmdb_ids = _tmdb_ids_used_by_show(session, episode)
    choices = [
        choice
        for candidate in candidates
        if (
            choice := _choice(
                candidate,
                absolute_numbers,
                _similarity(episode.name, candidate[0].name),
            )
        )
        is not None
    ]
    for choice in choices:
        choice.already_used = choice.tmdb_episode_id in used_tmdb_ids
    return sorted(
        choices,
        key=lambda choice: _order(choice.season_number, choice.episode_number),
    )
