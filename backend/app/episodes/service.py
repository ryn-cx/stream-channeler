# TODO: Validate
"""Which TMDB episode an `Episode` is a copy of, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

import re
import uuid
from collections import defaultdict
from collections.abc import Callable, Collection, Sequence
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy.orm import aliased, contains_eager, selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SHOW_LEVEL,
    is_tmdb_key,
    tmdb_id_of,
    tmdb_key_clause,
    tmdb_media_type_of,
)
from app.canonical_media.service import add_canonical_show
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
)
from app.episodes.schemas import (
    EpisodeUsingTmdb,
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
    UnmatchedEpisodesPublic,
)
from app.media.canonical_metadata import (
    tmdb_episode_url,
    tmdb_season_url,
    tmdb_show_url,
)
from app.media.identifiers import TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY
from app.media.media_type import MediaType
from app.media.name_forms import plaintext_forms
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.service import _apply_filter_options, _apply_sort_options
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source

if TYPE_CHECKING:
    # Read only for what it names here. The plugin is built on the base every
    # plugin is, which reads this module in turn, so importing it outright is a
    # circle - which is why what reaches for it does so where it is used.
    from plugins.TMDB import TMDB

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")

# How alike two names have to read before the closer of them is taken as the same
# episode, and how far ahead of the runner-up it has to be to be the one answer.
_SIMILAR_NAME_FLOOR = 0.5
_SIMILAR_NAME_LEAD = 0.1

# The two themoviedb.org addresses that name one record. On TMDB's own links the
# title's name follows its id, which is no part of what the page names and is
# left where it lies.
_FILM_URL = re.compile(r"themoviedb\.org/movie/(?P<tmdb_id>\d+)")
_SERIES_EPISODE_URL = re.compile(
    r"themoviedb\.org/tv/(?P<tmdb_id>\d+)[^/]*"
    r"/season/(?P<season_number>\d+)/episode/(?P<episode_number>\d+)",
)

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
# Held onto because a page of matches compares every episode against every
# candidate of its title, so the same handful of names are stripped down again
# for each pair - once per candidate per episode rather than once each.
@lru_cache(maxsize=16384)
def _plaintext(name: str | None) -> str:
    if not name:
        return ""
    return "".join(
        character
        for character in _untitled_number(name).casefold()
        if character.isalnum()
    )


# A website that writes an episode's place into its name - "Session #11 Toys in
# the Attic", "Episode 3 - Gateway Shuffle" - has said the number twice and the
# title once, and the number is no part of what the episode is called. Read off
# both sides, since it is only ever on one of them and taking it off a name that
# never carried it changes nothing.
#
# A word and a number, or a number written as one, rather than a bare number: a
# title opening on a year or a count is a title and not a place in a run.
_NUMBERED_NAME_PREFIX = re.compile(
    r"^\s*(?:(?:episode|ep|session|part)\s*\.?\s*#?\s*\d+|#\s*\d+)"
    r"\s*[-:.]?\s+",
    re.IGNORECASE,
)


# TODO: Validate
def _untitled_number(name: str) -> str:
    """Return `name` without the number a website wrote into the front of it.

    A name that is nothing but its number is left as it was: "Session #0" is what
    that episode is called, and taking the number out of it leaves nothing to
    match on at all.
    """
    untitled = _NUMBERED_NAME_PREFIX.sub("", name).strip()
    return untitled or name


# TODO: Validate
def _similarity(name: str | None, other_name: str | None) -> float:
    plaintext = _plaintext(name)
    other_plaintext = _plaintext(other_name)
    if not plaintext or not other_plaintext:
        return 0.0
    # The same name written the same way is the answer without the comparing,
    # which is the case an exact match takes and the costliest one to work out.
    if plaintext == other_plaintext:
        return 1.0

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
        canonical_episode_id=episode.id,
        season_id=season.id,
        show_id=show.id,
        tmdb_episode_id=tmdb_episode_id,
        name=episode.name,  # type: ignore[arg-type]
        show_name=show.name,  # type: ignore[arg-type]
        show_year=show.year,
        source_name=show.source.name,
        plugin_name=show.source.plugin.name,
        season_number=season.season_number,  # type: ignore[arg-type]
        episode_number=episode.episode_number,  # type: ignore[arg-type]
        absolute_number=absolute_numbers.get(episode.id),
        url=tmdb_episode_url(  # type: ignore[arg-type]
            show.key,
            season.season_number,
            episode.episode_number,
        ),
        show_url=tmdb_show_url(show.key),
        season_url=tmdb_season_url(show.key, season.season_number),
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
def _numbers_agree(
    episode: Episode,
    season: Season,
    own_absolute: int | None,
    candidate: _Candidate,
    candidate_absolute: int | None,
) -> bool:
    """Whether TMDB puts the episode where the website does, by any of its numbers.

    Compared across as well as like for like, since a website that numbers a
    title straight through calls TMDB's `S2E8` its own episode 57, so its
    episode number is answered by TMDB's count through the whole title rather
    than by TMDB's episode number.
    """
    candidate_episode, candidate_season, _show = candidate
    if (
        season.season_number is not None
        and episode.episode_number is not None
        and candidate_season.season_number == season.season_number
        and candidate_episode.episode_number == episode.episode_number
    ):
        return True
    if (
        episode.episode_number is not None
        and episode.episode_number == candidate_absolute
    ):
        return True
    return own_absolute is not None and own_absolute in (
        candidate_absolute,
        candidate_episode.episode_number,
    )


# TODO: Validate
def _number_match(
    episode: Episode,
    season: Season,
    candidates: list[_Candidate],
    absolute_numbers: dict[uuid.UUID, int],
    own_absolute: int | None,
) -> TmdbEpisodeChoice | None:
    """Return the TMDB episode numbered where `episode` is, or `None`.

    Read alongside the match made on the name rather than instead of it, since
    the two disagreeing is the whole of what somebody settling a row is being
    asked about: a name that matches and a number that does not is a title that
    reuses its episode names, and the other way round is a website numbering the
    title its own way.
    """
    for candidate in candidates:
        if _numbers_agree(
            episode,
            season,
            own_absolute,
            candidate,
            absolute_numbers.get(candidate[0].id),
        ):
            return _choice(
                candidate,
                absolute_numbers,
                _similarity(episode.name, candidate[0].name),
            )
    return None


# TODO: Validate
def _has_tmdb_title() -> ColumnElement[bool]:
    """Whether TMDB holds any of the titles the outer `Show` is a copy of.

    Any of them rather than one picked out of them, since a listing that mixes
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
# Which joined column each sortable name is, since a name a copy is not sorted
# by on its own row - the show it is under, the source that carries it - has no
# column of `Episode` to be read off.
_UNMATCHED_COLUMNS: dict[str, Any] = {
    # The combined column reads as the show it is under first, so that is what
    # sorting or filtering it is asking about.
    "summary": Show.name,
    "show_name": Show.name,
    "show_year": Show.year,
    "source_name": Source.name,
    "plugin_name": Plugin.name,
    "season_name": Season.name,
    "season_number": Season.season_number,
    "episode_name": Episode.name,
    "episode_number": Episode.episode_number,
    "identifier_note": Episode.canonical_episode_note,
}


# TODO: Validate
def _unmatched_base() -> SelectOfScalar[Episode]:
    """Every canonical episode of a plugin other than TMDB and YouTube.

    The rows the page is drawn from, before anything is sorted, filtered or
    counted. `contains_eager` carries the season, show and source back with each
    episode, since every one of them is read for every row and reaching them
    through the relationships would be three queries a row.
    """
    return (
        select(Episode)
        .select_from(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .options(
            contains_eager(Episode.season)  # type: ignore[arg-type]
            .contains_eager(Season.show)  # type: ignore[arg-type]
            .contains_eager(Show.source)  # type: ignore[arg-type]
            .contains_eager(Source.plugin),  # type: ignore[arg-type]
        )
        .where(
            # TMDB's own episodes are what everything else is matched against,
            # and YouTube's are nothing TMDB carries, so neither is waiting on a
            # match the way the rest are.
            col(Plugin.key).not_in((TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY)),
            is_canonical(Episode),
            # An episode settled as one TMDB has no record of points at nothing
            # and is locked there, which reads as canonical the same way one
            # nothing has worked out yet does. The lock is what tells them
            # apart, and a settled episode is waiting on nobody.
            col(Episode.canonical_episode_locked).is_(False),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
    )


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
    params: ReadOptions,
) -> UnmatchedEpisodesPublic:
    """Return a page of the canonical episodes outside TMDB and YouTube.

    Sorted, filtered and paged by the database rather than in the browser. There
    are far more of these than a page shows, so ordering a page of them would
    order only the ones already fetched: sorting by name would answer with the
    first names of whichever rows came back, not the first names there are.

    Always server-side, unlike the hybrid tables. The closest TMDB episode is
    worked out by comparing names in Python, which is worth doing for the twenty
    rows being shown and not for every row there is.
    """
    filtered = _apply_filter_options(
        _unmatched_base(),
        params.filter_options,
        _UNMATCHED_COLUMNS,
    )
    total_count = session.exec(
        select(func.count()).select_from(_unmatched_base().subquery()),
    ).one()
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            _UNMATCHED_COLUMNS,
            Episode.created_at,
            Episode.id,
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    episodes = list(session.exec(page).all())
    return UnmatchedEpisodesPublic(
        data=_unmatched_outputs(session, episodes),
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )


# TODO: Validate
def _unmatched_outputs(
    session: Session,
    episodes: list[Episode],
) -> list[UnmatchedEpisodeOutput]:
    """Describe each episode of a page, beside the TMDB episode closest to it."""
    rows = [
        (episode, episode.season, episode.season.show, episode.season.show.source)
        for episode in episodes
    ]
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
            show_year=show.year,
            show_url=show.url,
            season_url=season.url,
            source_id=source.id,
            source_name=source.name,
            plugin_name=source.plugin.name,
            url=episode.url,
            best_match=_best_match(
                episode,
                season,
                candidates.get(show.id, []),
                candidate_numbers.get(show.id, {}),
            ),
            number_match=_number_match(
                episode,
                season,
                candidates.get(show.id, []),
                candidate_numbers.get(show.id, {}),
                source_numbers.get(episode.id),
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
                show_year=show.year,
                show_url=show.url,
                season_url=season.url,
                source_id=source.id,
                source_name=source.name,
                plugin_name=source.plugin.name,
                url=episode.url,
                best_match=best_match,
                number_match=_number_match(
                    episode,
                    season,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                    source_numbers.get(episode.id),
                ),
                name_matches=bool(
                    best_match
                    and _plaintext(episode.name)
                    and _plaintext(episode.name) == _plaintext(best_match.name),
                ),
            ),
        )
    return outputs


# TODO: Validate
def _tmdb_ids_used_by_show(
    session: Session,
    episode: Episode,
) -> dict[int, list[EpisodeUsingTmdb]]:
    """Return the episodes of `episode`'s show using each TMDB episode already.

    Only the show the episode belongs to is read, since another website's copy
    of the same title has its own episodes pointing at the same TMDB ones and
    says nothing about which of them this show still has going spare. The
    episode being linked is left out so the record it already points at is not
    counted as somebody else's.
    """
    canonical_episode = aliased(Episode)
    statement = (
        select(canonical_episode.key, Episode, Season)  # type: ignore[call-overload]
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
    using: dict[int, list[EpisodeUsingTmdb]] = defaultdict(list)
    for key, used_by, season in session.exec(statement).all():
        tmdb_id = tmdb_id_of(key, EPISODE_LEVEL)
        if tmdb_id is None:
            continue
        using[tmdb_id].append(
            EpisodeUsingTmdb(
                id=used_by.id,
                name=used_by.name,
                season_number=season.season_number,
                episode_number=used_by.episode_number,
                url=used_by.url,
            ),
        )
    return using


# TODO: Validate
def _import_tmdb_show(session: Session, media_type: MediaType, tmdb_id: int) -> Show:
    """Read a TMDB title in and return the row standing for it.

    Read in rather than looked for, since a title nothing has imported has no
    episodes stored to choose from and naming it is the asking for it. Whatever
    is already stored costs nothing to ask for again.

    Imported here rather than at the top of the module because the TMDB plugin
    is built on the base every plugin is, which reads this module in turn.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    tmdb = TMDB(session)
    if media_type is MediaType.movie:
        return tmdb.import_movie(tmdb_id)
    return tmdb.import_show(tmdb_id)


# TODO: Validate
def _import_tmdb_url(session: Session, url: str) -> Show:
    """Read the title a themoviedb.org address is under in, and return its row.

    Which half of the catalogue an address names and which title is the plugin's
    to read, so the address is handed over whole rather than taken apart first. A
    season and an episode are under the title rather than beside it, so an
    address naming one reads the title in exactly as the title's own page would.

    Imported here rather than at the top of the module because the TMDB plugin
    is built on the base every plugin is, which reads this module in turn.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    imported = TMDB(session).import_url(url)
    statement = select(Show).where(
        is_canonical(Show),
        Show.key == imported[0].show_key,
    )
    return session.exec(statement).one()


# TODO: Validate
def _imported_title(session: Session, tmdb_show_id: int) -> uuid.UUID:
    """Read a TMDB series in and return the title its episodes are under."""
    return _import_tmdb_show(session, MediaType.tv, tmdb_show_id).id


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
        choice.used_by = used_tmdb_ids.get(choice.tmdb_episode_id, [])
        choice.already_used = bool(choice.used_by)
    return sorted(
        choices,
        key=lambda choice: _order(choice.season_number, choice.episode_number),
    )


# TODO: Validate
def link_episode_using_tmdb_url(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    """Point `episode` at the TMDB record a themoviedb.org address names.

    Only a film's page and a series episode's page are taken, since they are the
    addresses that name one record: a series page names a title rather than any
    of its episodes, and a season's names a run of them, so neither says what
    `episode` is a copy of. Which of the two was given is settled here, and the
    address is handed on to whichever reads it.
    """
    address = url.strip()
    if found := _SERIES_EPISODE_URL.search(address):
        return _link_episode_using_tmdb_episode(session, episode, address, found)
    if _FILM_URL.search(address):
        return _link_episode_using_tmdb_movie(session, episode, address)

    raise HTTPException(
        status_code=400,
        detail=f"{url} is not the address of a TMDB film or series episode",
    )


# TODO: Validate
def _link_episode_using_tmdb_episode(
    session: Session,
    episode: Episode,
    url: str,
    found: re.Match[str],
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)
    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(Episode),
            Season.show_id == canonical_show.id,
            Season.season_number == int(found["season_number"]),
            Episode.episode_number == int(found["episode_number"]),
        ),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def _link_episode_using_tmdb_movie(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)

    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(is_canonical(Episode), Season.show_id == canonical_show.id),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def link_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> Episode:
    """Point every listing of `episode`'s media at a TMDB episode.

    A `User` saying which TMDB episode this is has said it of the media rather
    than of the one row they happened to be looking at, and `watch_identifier`
    is what says two rows are of the same media. So every row carrying that
    identifier is pointed at the record together, which is what stops the same
    decision having to be made again for each website carrying the episode.
    """
    for same_media in _episodes_sharing_identifier(session, episode):
        _link_one_episode(session, same_media, canonical_episode)

    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _episodes_sharing_identifier(session: Session, episode: Episode) -> list[Episode]:
    """Return every stored listing of the media `episode` is a listing of."""
    return list(
        session.exec(
            select(Episode).where(
                Episode.watch_identifier == episode.watch_identifier,
                col(Episode.deleted_at).is_(None),
            ),
        ).all(),
    )


# TODO: Validate
def _link_one_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> None:
    """Point one `Episode` at a TMDB episode, and its show at the title holding it.

    Two websites' episodes pointing at one record is what makes them a single
    episode to watch, so only the show's own other episodes are a clash. A `User`
    saying which episode the record is has settled which one it is, so whichever
    was on it by a guess comes off and is left for the next import to match
    again. An episode another `User` decision put there is left where it is,
    since one decision is no reason to undo another.
    """
    add_canonical_show(session, episode.season.show, canonical_episode.season.show)

    others = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            Season.show_id == episode.season.show_id,
            Episode.canonical_episode_id == canonical_episode.id,
            Episode.id != episode.id,
            col(Episode.deleted_at).is_(None),
        ),
    ).all()
    for other in others:
        if other.canonical_episode_locked and (
            other.canonical_episode_note or ""
        ).startswith(MANUAL_NOTE_PREFIX):
            continue

        removed = (
            f"Removed {canonical_episode.id}, which was given to another "
            "episode by hand"
        )
        previous = other.canonical_episode_note
        other.canonical_episode_note = f"{removed}. {previous}" if previous else removed
        other.canonical_episode = None
        other.canonical_episode_locked = False
        session.add(other)

    # Taken off before the episode being linked is put on, since the two hold
    # the record one after the other and a season may hold both of them.
    session.flush()

    episode.canonical_episode_id = canonical_episode.id
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = "Manual: Selection"
    session.add(episode)


# TODO: Validate
def unlink_episode(session: Session, episode: Episode) -> Episode:
    """Take `episode` off the TMDB episode it was pointed at.

    The lock and the note go with it, so the episode is left as one nothing has
    settled rather than as one settled at nothing: a link taken back is a link
    that should not have been made, and the next import is free to work out its
    own again.
    """
    episode.canonical_episode = None
    episode.canonical_episode_locked = False
    episode.canonical_episode_note = None
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def mark_episode_absent_from_tmdb(session: Session, episode: Episode) -> Episode:
    """Settle `episode` as one TMDB has no record of.

    Pointed at nothing and locked there, which is what says the emptiness was
    decided rather than not yet worked out: an import leaves an episode it could
    not place pointing at nothing too, and only the lock tells the two apart. The
    note says who decided, so it carries the manual prefix the same way a link
    chosen by hand does.
    """
    episode.canonical_episode = None
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Not on TMDB"
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _own_episode_numbers(tmdb_episode: Episode) -> Collection[int]:
    """The number a TMDB episode carries in the order its title is read in."""
    if tmdb_episode.episode_number is None:
        return ()
    return (tmdb_episode.episode_number,)


# TODO: Validate
def _canonical_episodes_by_name_and_number(
    canonical_episodes: Collection[Episode],
    name_of: Callable[[Episode], str | None],
    numbers_of: Callable[[Episode], Collection[int]],
) -> dict[tuple[str, int], Episode]:
    candidates: dict[tuple[str, int], Episode] = {}
    ambiguous: set[tuple[str, int]] = set()
    for tmdb_episode in canonical_episodes:
        name = name_of(tmdb_episode)
        if not name:
            continue
        for episode_number in numbers_of(tmdb_episode):
            pairing = (name, episode_number)
            if pairing in candidates:
                ambiguous.add(pairing)
                continue
            candidates[pairing] = tmdb_episode
    # Two TMDB episodes sharing a name and a number say nothing about which of
    # them an episode is, so neither is offered.
    for pairing in ambiguous:
        del candidates[pairing]
    return candidates


# TODO: Validate
def _canonical_episodes_by_name(
    canonical_episodes: Collection[Episode],
    name_of: Callable[[Episode], str | None],
) -> dict[str, Episode]:
    candidates: dict[str, Episode] = {}
    ambiguous: set[str] = set()
    for tmdb_episode in canonical_episodes:
        name = name_of(tmdb_episode)
        if not name:
            continue
        if name in candidates:
            ambiguous.add(name)
            continue
        candidates[name] = tmdb_episode
    # Two TMDB episodes sharing a name say nothing about which of them an episode
    # is, so neither is offered.
    for name in ambiguous:
        del candidates[name]
    return candidates


# TODO: Validate
def _best_name_similarity(
    episode: Episode,
    tmdb_episode: Episode,
    translated_forms: frozenset[str],
) -> float:
    """Return how alike the two episodes are read across every name either carries."""
    best = _similarity(episode.name, tmdb_episode.name)
    for form in plaintext_forms(episode.name):
        for translated_form in translated_forms:
            best = max(best, _similarity(form, translated_form))
    return best


# TODO: Validate
def _translated_forms_cache(session: Session) -> dict[uuid.UUID, frozenset[str]]:
    """Every spelling of every language's name for a TMDB episode, by episode.

    Kept on the session rather than on the linker, because a linker is built
    afresh for every show that is read and each of them wants the translations of
    the same canonical episodes. Reading them once per session is what keeps a
    run that reads one show a hundred times from reading them a hundred times.
    """
    cache: dict[uuid.UUID, frozenset[str]] = session.info.setdefault(
        "translated_episode_name_forms",
        {},
    )
    return cache


# TODO: Validate
def _alternate_numbers_cache(session: Session) -> dict[int, dict[int, frozenset[int]]]:
    """Every number each TMDB episode carries in another order, by title.

    Kept on the session for the same reason the translations are: a linker is
    built afresh for every show that is read, and every copy of one title asks
    for the same title's orders.
    """
    cache: dict[int, dict[int, frozenset[int]]] = session.info.setdefault(
        "alternate_tmdb_episode_numbers",
        {},
    )
    return cache


# TODO: Validate
class EpisodeLinker:
    """Points a show's episodes at the canonical TMDB episodes they answer to.

    The matchers are read in turn, from the one that asks the most of a pair to
    the one that asks the least, and each is handed only what the one before it
    could not place. An episode that has been linked is dropped there and then,
    so the looser and costlier a matcher is the fewer episodes it has to read.
    """

    # TODO: Validate
    def __init__(self, session: Session, show: Show) -> None:
        """Gather the show's episodes and the canonical ones they are read against."""
        self.session = session
        self.show = show
        self.episodes = [
            episode
            for season in show.active_children
            for episode in season.active_children
        ]
        # A canonical episode one of the show's episodes already names is spoken
        # for, and handing it to a second episode is the one thing the database
        # will not hold. It is still read against, though: which episode a row is
        # closest to is the whole of what a matcher decides, and an episode that
        # cannot see the record it is really of reads as the best match for
        # whichever record is left, which is how a row nothing had recognised
        # ends up wearing another episode's name.
        self.claimed_canonical_ids = {
            episode.canonical_episode_id
            for episode in self.episodes
            if episode.canonical_episode_id
        }
        self.canonical_episodes = [
            episode
            for canonical_show in show.canonical_shows
            for season in canonical_show.active_children
            for episode in season.active_children
            if is_tmdb_key(episode.key)
        ]
        self._load_existing_links([*self.episodes, *self.canonical_episodes])
        # Read off the TMDB plugin the first time a matcher asks for them, since
        # two of them want the same translations and neither always runs.
        self._translated_forms: dict[uuid.UUID, frozenset[str]] | None = None
        # Read off the TMDB plugin the same way and for the same reason: three
        # matchers read the other orders and none of them always runs.
        self._alternate_numbers: dict[uuid.UUID, frozenset[int]] | None = None

    # TODO: Validate
    def _load_existing_links(self, episodes: Sequence[Episode]) -> None:
        """Settle what each episode already stands for without reading one at a time.

        Writing a link is a write the database works out the whole of only once
        it knows what the episode stood for before, so an episode whose link has
        not been read is one it goes and reads while writing - a query each, in
        the middle of the flush.

        An episode standing for nothing is settled here rather than read at all.
        `Episode.id` is unique rather than the primary key, which is what leaves
        the database unable to answer a link out of what it is already holding -
        and unable even to skip the reading of a link that is empty, which is a
        query that can only ever come back with nothing. Every canonical row has
        an empty link, so that is most of them.

        The rest are read together, which is one query rather than one apiece.
        """
        unread = [
            episode
            for episode in episodes
            if "canonical_episode" in instance_state(episode).unloaded
        ]
        for episode in unread:
            if episode.canonical_episode_id is None:
                set_committed_value(episode, "canonical_episode", None)

        linked = [
            episode.id for episode in unread if episode.canonical_episode_id is not None
        ]
        if not linked:
            return
        self.session.exec(
            select(Episode)
            .where(col(Episode.id).in_(linked))
            .options(selectinload(Episode.canonical_episode)),  # type: ignore[arg-type]
        ).all()

    # TODO: Validate
    def link(self) -> None:
        """Link each of the show's episodes to its canonical episode, where one is.

        The numbering matchers are read twice over: once against the numbering
        the title is stored in, and once against every other order TMDB holds for
        it. A website following the DVD order numbers an episode where that order
        puts it, which is a number the title's own seasons never gave it, so the
        pair only ever line up once the other orders are read too. The title's own
        numbering is read first either way, since an episode that lines up under
        the order the title is stored in is not one another order gets a say in.
        """
        self._link_to_movie()
        self._link_by_name_and_episode_number()
        self._link_by_plaintext_name_and_episode_number()
        self._link_by_name_and_alternate_number()
        self._link_by_plaintext_name_and_alternate_number()
        self._link_by_similar_name_and_episode_number()
        self._link_by_similar_name_and_alternate_number()
        self._link_by_name()
        self._link_by_plaintext_name()
        self._link_by_translated_name()

    # TODO: Validate
    def _drop_linked(self) -> None:
        """Leave only the episodes still waiting on a canonical episode."""
        self.episodes = [
            episode for episode in self.episodes if not episode.canonical_episode_id
        ]

    # TODO: Validate
    def _claim(self, episode: Episode, tmdb_episode: Episode, note: str) -> None:
        """Point the episode at the canonical episode and take it off the table.

        Two episodes of a show naming the one canonical episode is the one thing
        the database will not hold, so the first of them to be read takes it and
        the rest are left waiting for a matcher that can tell them apart.

        A canonical episode already spoken for is noted rather than taken out of
        what is read against, so an episode whose own record has gone is left
        waiting instead of being handed the nearest record still going: what a
        matcher was asked was which episode this is, and the answer to that does
        not change because somebody else got there first.

        The pointer is written as well as the record it points at, since what an
        episode has been given is read back off the pointer before any of this is
        written down. Leaving it to be filled in at the writing is what had a
        matched episode read as one still waiting: it was handed on to the
        matchers after, each of which gave it another canonical episode and left
        the one before it taken by nothing.
        """
        if tmdb_episode.id in self.claimed_canonical_ids:
            return
        self.claimed_canonical_ids.add(tmdb_episode.id)
        episode.canonical_episode = tmdb_episode
        episode.canonical_episode_id = tmdb_episode.id
        episode.canonical_episode_note = note

    # TODO: Validate
    def _translated_name_forms(self) -> dict[uuid.UUID, frozenset[str]]:
        """Return every spelling of every language's name for each TMDB episode.

        An episode's translations are the one thing about a TMDB episode that is
        not stored alongside it, so they are read off the plugin rather than the
        row.

        Read once per session and remembered there, so the plugin is built and
        the translations are reached for only for the episodes nothing has read
        yet. A run that reads one show over and over reads them the first time
        and takes them off the session after that.

        Imported here rather than at the top of the module because the TMDB
        plugin is built on the base every plugin is, which reads this module in
        turn.
        """
        if self._translated_forms is not None:
            return self._translated_forms

        cache = _translated_forms_cache(self.session)
        unread = [
            tmdb_episode
            for tmdb_episode in self.canonical_episodes
            if tmdb_episode.id not in cache
        ]
        if unread:
            from plugins.TMDB import TMDB  # noqa: PLC0415

            tmdb = TMDB(self.session)
            numberings = {
                tmdb_episode.id: self._episode_numbering(tmdb_episode)
                for tmdb_episode in unread
            }
            # Held for as long as the names are being read, because the session
            # keeps its records weakly and a row nothing is holding is dropped
            # and read again one at a time - which is what this read replaces.
            _rows = tmdb.preload_episode_translations(
                [
                    numbering
                    for numbering in numberings.values()
                    if numbering is not None
                ],
            )
            for tmdb_episode in unread:
                cache[tmdb_episode.id] = self._episode_name_forms(
                    tmdb,
                    numberings[tmdb_episode.id],
                )

        self._translated_forms = {
            tmdb_episode.id: cache[tmdb_episode.id]
            for tmdb_episode in self.canonical_episodes
        }
        return self._translated_forms

    # TODO: Validate
    def _alternate_episode_numbers(self) -> dict[uuid.UUID, frozenset[int]]:
        """Return every number each canonical episode carries in another order.

        The orders are TMDB's own and are read off the plugin, since a row holds
        the numbering of the one order its title is stored in and nothing of the
        rest. Every title the show is a copy of is read, so a listing that mixes
        titles is matched against the orders of each of them.

        Read once per title per session and remembered there, so a run that reads
        one title over and over reads its orders the first time and takes them
        off the session after that.

        Imported here rather than at the top of the module because the TMDB
        plugin is built on the base every plugin is, which reads this module in
        turn.
        """
        if self._alternate_numbers is not None:
            return self._alternate_numbers

        from plugins.TMDB import TMDB  # noqa: PLC0415

        cache = _alternate_numbers_cache(self.session)
        tmdb = TMDB(self.session)
        by_tmdb_id: dict[int, frozenset[int]] = {}
        for canonical_show in self.show.canonical_shows:
            tmdb_show_id = tmdb_id_of(canonical_show.key, SHOW_LEVEL)
            media_type = tmdb_media_type_of(canonical_show.key, SHOW_LEVEL)
            # A film is one episode of one season however it is read, so there is
            # no other order for it to be in.
            if tmdb_show_id is None or media_type is not MediaType.tv:
                continue
            if tmdb_show_id not in cache:
                cache[tmdb_show_id] = tmdb.alternate_episode_numbers(tmdb_show_id)
            by_tmdb_id |= cache[tmdb_show_id]

        self._alternate_numbers = {}
        for tmdb_episode in self.canonical_episodes:
            tmdb_episode_id = tmdb_id_of(tmdb_episode.key, EPISODE_LEVEL)
            if tmdb_episode_id is None:
                continue
            if numbers := by_tmdb_id.get(tmdb_episode_id):
                self._alternate_numbers[tmdb_episode.id] = numbers
        return self._alternate_numbers

    # TODO: Validate
    def _alternate_numbers_of(self, tmdb_episode: Episode) -> Collection[int]:
        """The numbers a TMDB episode carries in TMDB's other orders of its title."""
        return self._alternate_episode_numbers().get(tmdb_episode.id, frozenset())

    # TODO: Validate
    @staticmethod
    def _episode_numbering(tmdb_episode: Episode) -> tuple[int, int, int] | None:
        """What TMDB is asked about one episode by, where it can be asked at all.

        An episode whose title, season or number is not known is one TMDB has no
        answer for, and says so by having no numbering rather than a partial one.
        """
        season = tmdb_episode.season
        tmdb_show_id = tmdb_id_of(season.show.key, SHOW_LEVEL)
        if (
            tmdb_show_id is None
            or season.season_number is None
            or tmdb_episode.episode_number is None
        ):
            return None
        return (tmdb_show_id, season.season_number, tmdb_episode.episode_number)

    # TODO: Validate
    @staticmethod
    def _episode_name_forms(
        tmdb: TMDB,
        numbering: tuple[int, int, int] | None,
    ) -> frozenset[str]:
        """Return every spelling of every language's name for one TMDB episode.

        An episode TMDB cannot be asked about has no names rather than none
        recorded, which is the same thing to everything that reads them and is
        what keeps it from being asked about again.
        """
        if numbering is None:
            return frozenset()
        return frozenset(
            form
            for name in tmdb.translated_episode_names(*numbering)
            for form in plaintext_forms(name)
        )

    # TODO: Validate
    def _link_to_movie(self) -> None:
        """Point a lone episode at a lone TMDB episode, and leave nothing for the rest.

        A film is one episode of one season on both sides, so a row with a single
        episode against a canonical show with a single episode is matched
        outright: there is nothing else either of them could be, whatever the two
        are named. Once that has been read the episode is settled either way, so
        nothing is left for the matchers that follow to read a second time.
        """
        if len(self.episodes) != 1 or len(self.canonical_episodes) != 1:
            self._drop_linked()
            return

        only_episode = self.episodes[0]
        if (
            only_episode.canonical_episode_id is None
            and not only_episode.canonical_episode_locked
        ):
            self._claim(
                only_episode,
                self.canonical_episodes[0],
                "Automatic: Movie match",
            )
        self.episodes = []

    # TODO: Validate
    def _link_by_name_and_number(
        self,
        name_of: Callable[[Episode], str | None],
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> None:
        """Point each episode at the TMDB episode of its name and one of its numbers."""
        sorted_canonical_episodes = _canonical_episodes_by_name_and_number(
            self.canonical_episodes,
            name_of,
            numbers_of,
        )
        for episode in self.episodes:
            pairing = (name_of(episode), episode.episode_number)
            if match := sorted_canonical_episodes.get(pairing):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
                self._claim(episode, match, note)
        self._drop_linked()

    # TODO: Validate
    def _link_by_name_and_episode_number(self) -> None:
        """Point each episode at the TMDB episode of the same name and number."""
        self._link_by_name_and_number(
            lambda tmdb_episode: tmdb_episode.name,
            _own_episode_numbers,
            "Automatic: Name and number match",
        )

    # TODO: Validate
    def _link_by_plaintext_name_and_episode_number(self) -> None:
        """Point each episode at the TMDB episode of the same name and number.

        The names are compared with their case, punctuation and spacing taken
        out, so "The One With the Cat" and "the one with the cat!" are the one
        name they are both a spelling of and the episode is matched rather than
        left waiting.
        """
        self._link_by_name_and_number(
            lambda tmdb_episode: _plaintext(tmdb_episode.name),
            _own_episode_numbers,
            "Automatic: Plaintext name and number match",
        )

    # TODO: Validate
    def _link_by_name_and_alternate_number(self) -> None:
        """Point each episode at the TMDB episode of its name, in any other order.

        The number the website wrote down is read against every order TMDB holds
        for the title rather than against the one the title is stored in, so an
        episode numbered by the DVD order or counted straight through the run is
        matched by the number that order gives it.
        """
        if not self.episodes:
            return
        self._link_by_name_and_number(
            lambda tmdb_episode: tmdb_episode.name,
            self._alternate_numbers_of,
            "Automatic: Name and alternate order number match",
        )

    # TODO: Validate
    def _link_by_plaintext_name_and_alternate_number(self) -> None:
        """Point each episode at the TMDB episode of its name, in any other order.

        The same as matching on a name and another order's number, with the case,
        punctuation and spacing of the name taken out of it.
        """
        if not self.episodes:
            return
        self._link_by_name_and_number(
            lambda tmdb_episode: _plaintext(tmdb_episode.name),
            self._alternate_numbers_of,
            "Automatic: Plaintext name and alternate order number match",
        )

    # TODO: Validate
    def _link_by_name(self) -> None:
        """Point each episode at the TMDB episode of the same name.

        The numbering is no part of it, so an episode a website filed under a
        number of its own is still matched by the one thing the two of them agree
        on.
        """
        sorted_canonical_episodes = _canonical_episodes_by_name(
            self.canonical_episodes,
            lambda tmdb_episode: tmdb_episode.name,
        )
        for episode in self.episodes:
            if match := sorted_canonical_episodes.get(episode.name):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
                self._claim(episode, match, "Automatic: Name match")
        self._drop_linked()

    # TODO: Validate
    def _link_by_plaintext_name(self) -> None:
        """Point each episode at the TMDB episode of the same name.

        Neither the numbering nor the case, punctuation and spacing of the name
        are any part of it, which is the loosest either of them can be matched
        on.
        """
        sorted_canonical_episodes = _canonical_episodes_by_name(
            self.canonical_episodes,
            lambda tmdb_episode: _plaintext(tmdb_episode.name),
        )
        for episode in self.episodes:
            if match := sorted_canonical_episodes.get(_plaintext(episode.name)):
                self._claim(episode, match, "Automatic: Plaintext name match")
        self._drop_linked()

    # TODO: Validate
    def _link_by_translated_name(self) -> None:
        """Point each episode at the TMDB episode named that in any language.

        A website carries the name the episode is known by where it is watched,
        which is the Japanese name of a Japanese title on one site and the
        English name of the same episode on the next, and neither is the name the
        other wrote down. TMDB holds every language's name for an episode, so an
        episode is matched against all of them rather than against the one
        language its row was read in.

        Each name is compared as every spelling it could be written in, so a name
        written in kana on one side and romanised on the other is still the one
        name the two of them are. Two TMDB episodes answering to the same name
        say nothing about which of them an episode is, so neither is taken.
        """
        if not self.episodes:
            return

        forms_by_tmdb_episode = self._translated_name_forms()
        for episode in self.episodes:
            if not (targets := plaintext_forms(episode.name)):
                continue

            matches = [
                tmdb_episode
                for tmdb_episode in self.canonical_episodes
                if forms_by_tmdb_episode.get(tmdb_episode.id, frozenset()) & targets
            ]
            if len(matches) != 1:
                continue
            self._claim(episode, matches[0], "Automatic: Translated name match")
        self._drop_linked()

    # TODO: Validate
    def _link_by_similar_name_and_alternate_number(self) -> None:
        """Point each episode at the closest named TMDB episode of another order.

        The same as matching on a similar name and a number, with the number read
        against every order TMDB holds for the title rather than against the one
        the title is stored in.
        """
        if not self.episodes:
            return
        self._link_by_similar_name(
            self._alternate_numbers_of,
            "Automatic: Similar name and alternate order number match",
        )

    # TODO: Validate
    def _link_by_similar_name_and_episode_number(self) -> None:
        """Point each episode at the closest named TMDB episode of its number.

        The name a website wrote down is the name of the episode as somebody
        typed it, which is the official name with a word dropped, a subtitle
        added or a spelling of its own, and none of those are the name TMDB holds
        letter for letter. Every name either side carries is read here, the
        official one and every language's, and the closest of them decides it.

        Only episodes sharing a number are considered, so the numbering carries
        the weight the name no longer can. A name has to be alike enough to mean
        something and has to be clearly ahead of the next best, or the episode is
        left waiting.
        """
        self._link_by_similar_name(
            _own_episode_numbers,
            "Automatic: Similar name and number match",
        )

    # TODO: Validate
    def _link_by_similar_name(
        self,
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> None:
        """Point each episode at the closest named TMDB episode carrying its number."""
        numbered_episodes = [
            episode for episode in self.episodes if episode.episode_number is not None
        ]
        if not numbered_episodes:
            return

        forms_by_tmdb_episode = self._translated_name_forms()
        for episode in numbered_episodes:
            scored = sorted(
                (
                    (
                        _best_name_similarity(
                            episode,
                            tmdb_episode,
                            forms_by_tmdb_episode.get(tmdb_episode.id, frozenset()),
                        ),
                        tmdb_episode,
                    )
                    for tmdb_episode in self.canonical_episodes
                    if episode.episode_number in numbers_of(tmdb_episode)
                ),
                key=lambda scoring: scoring[0],
                reverse=True,
            )
            if not scored or scored[0][0] < _SIMILAR_NAME_FLOOR:
                continue
            if len(scored) > 1 and scored[0][0] - scored[1][0] < _SIMILAR_NAME_LEAD:
                continue

            self._claim(episode, scored[0][1], note)
        self._drop_linked()
