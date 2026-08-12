# TODO: Validate
"""Episodes no TMDB record was found for, each beside the closest TMDB episode.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered
here, each paired with the TMDB episode that came closest, so the link a name
could not make can be made by hand instead.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from difflib import SequenceMatcher

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SHOW_LEVEL,
    not_tmdb_key_clause,
    parse_tmdb_key,
    tmdb_episode_key,
    tmdb_id_of,
    tmdb_key_clause,
)
from app.canonical_media.service import point_episode_at, standalone_episode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import (
    MANUAL_NOTES,
    MANUALLY_CONFIRMED_NOTE,
    MANUALLY_SELECTED_NOTE,
    NO_MATCH_NOTE,
    Episode,
)
from app.episodes.schemas import (
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
)
from app.media.canonical_metadata import tmdb_episode_url
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")

# What an `Episode` can be pointed at: the episode itself, the season holding
# it, and the title above that, all as TMDB has them.
type _Candidate = tuple[CanonicalEpisode, CanonicalSeason, CanonicalShow]
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
def _unmatched_rows(
    session: Session,
    limit: int,
) -> list[tuple[Episode, Season, Show, Source]]:
    statement = (
        select(Episode, Season, Show, Source)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .join(
            CanonicalEpisode,
            onclause=col(Episode.canonical_episode_id) == CanonicalEpisode.id,
        )
        .join(
            CanonicalShow,
            onclause=col(Show.canonical_show_id) == CanonicalShow.id,
        )
        .where(
            Plugin.key != TMDB_PLUGIN_KEY,
            # The episode is a copy of something TMDB has no record of, while
            # the title above it is one TMDB does hold: that gap is exactly what
            # is left to match.
            not_tmdb_key_clause(col(CanonicalEpisode.key)),
            tmdb_key_clause(col(CanonicalShow.key)),
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
        select(CanonicalEpisode, CanonicalSeason, CanonicalShow)
        .join(
            CanonicalSeason,
            onclause=col(CanonicalEpisode.canonical_season_id) == CanonicalSeason.id,
        )
        .join(
            CanonicalShow,
            onclause=col(CanonicalSeason.canonical_show_id) == CanonicalShow.id,
        )
        .where(
            col(CanonicalShow.id).in_(canonical_show_ids),
            tmdb_key_clause(col(CanonicalEpisode.key)),
        )
    )
    candidates: dict[uuid.UUID, list[_Candidate]] = defaultdict(list)
    for episode, season, show in session.exec(statement).all():
        candidates[show.id].append((episode, season, show))
    return candidates


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
    candidates = _candidates_by_show(
        session,
        {
            show.canonical_show_id
            for _episode, _season, show, _source in rows
            if show.canonical_show_id
        },
    )
    candidate_numbers = {
        canonical_show_id: _candidate_absolute_numbers(show_candidates)
        for canonical_show_id, show_candidates in candidates.items()
    }
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
                candidates.get(show.canonical_show_id, []),
                candidate_numbers.get(show.canonical_show_id, {}),
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
            tmdb_key_clause(col(CanonicalShow.key)),
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
    candidates = _candidates_by_show(
        session,
        {
            show.canonical_show_id
            for _episode, _season, show, _source in rows
            if show.canonical_show_id
        },
    )
    candidate_numbers = {
        canonical_show_id: _candidate_absolute_numbers(show_candidates)
        for canonical_show_id, show_candidates in candidates.items()
    }
    source_numbers = _source_absolute_numbers(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    outputs: list[UnlockedEpisodeOutput] = []
    for episode, season, show, source in rows:
        best_match = _best_match(
            episode,
            season,
            candidates.get(show.canonical_show_id, []),
            candidate_numbers.get(show.canonical_show_id, {}),
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
    statement = (
        select(CanonicalEpisode.key)
        .join(
            Episode,
            onclause=col(Episode.canonical_episode_id) == CanonicalEpisode.id,
        )
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            Season.show_id == episode.season.show_id,
            col(Episode.id) != episode.id,
            tmdb_key_clause(col(CanonicalEpisode.key)),
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

    canonical_show = TMDB(session).import_title(MediaType.tv, tmdb_show_id)
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

    The title is the one the episode's show is linked to, unless another is named
    outright. TMDB files some episodes under a title of their own, so an episode
    is not always among the episodes of the title its show is, and naming the
    title it is under is the only way to reach it.
    """
    canonical_show_id = (
        episode.season.show.canonical_show_id
        if tmdb_show_id is None
        else _imported_title(session, tmdb_show_id)
    )
    if canonical_show_id is None:
        return []
    candidates = _candidates_by_show(session, {canonical_show_id}).get(
        canonical_show_id,
        [],
    )
    absolute_numbers = _candidate_absolute_numbers(candidates)
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


# TODO: Validate
def _tmdb_halves(media_type: MediaType | None) -> list[MediaType]:
    """Return the halves of the catalogue an id could belong to."""
    return [media_type] if media_type is not None else list(MediaType)


# TODO: Validate
def _tmdb_episode(
    session: Session,
    tmdb_episode_id: int,
    media_type: MediaType | None = None,
) -> CanonicalEpisode | None:
    """Return the imported TMDB episode an id names, in one half of the catalogue.

    An id said to be a movie's is only ever looked for as a movie, so a series
    episode that happens to carry the same number is never taken for it, and the
    other way about. An id with neither said of it is looked for as both, which
    is what a choice taken off the list is.
    """
    statement = select(CanonicalEpisode).where(
        col(CanonicalEpisode.key).in_(
            [
                tmdb_episode_key(half, tmdb_episode_id)
                for half in _tmdb_halves(media_type)
            ],
        ),
    )
    return session.exec(statement).first()


# TODO: Validate
def link_episode(
    session: Session,
    episode: Episode,
    tmdb_episode_id: int,
    *,
    media_type: MediaType | None = None,
    selected: bool = False,
) -> Episode:
    """Point `episode` at a TMDB episode a `User` chose, and hold it there.

    The episode is pointed at the row already read in rather than at one built
    from the id given, so an id TMDB has nothing imported for is refused instead
    of stored as a link to a record that will never fill anything in. The link is
    locked, which is what keeps the next import's own guess from replacing it.

    `selected` says the `User` went and found the episode rather than taking the
    one they were shown, which is the note the link is left with.
    """
    _import_named_media(session, episode, tmdb_episode_id, media_type)

    counterpart = _tmdb_episode(session, tmdb_episode_id, media_type)
    if counterpart is None:
        halves = " or ".join(sorted(str(half) for half in _tmdb_halves(media_type)))
        raise HTTPException(
            status_code=404,
            detail=(
                f"TMDB has no imported episode with the id {tmdb_episode_id} "
                f"as a {halves}"
            ),
        )

    _unlink_others_sharing(session, episode, counterpart.id)

    episode.canonical_episode_locked = True
    episode.canonical_episode_note = (
        MANUALLY_SELECTED_NOTE if selected else MANUALLY_CONFIRMED_NOTE
    )
    session.add(episode)
    point_episode_at(session, episode, counterpart)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _import_named_media(
    session: Session,
    episode: Episode,
    tmdb_episode_id: int,
    media_type: MediaType | None,
) -> None:
    """Read in from TMDB whatever holds the episode an id names.

    A `User` writing an id by hand has no reason to have imported what holds it
    first, and an episode is only there to be linked to once it has been read in.
    Whatever is already imported is left as it is, so this costs nothing when the
    episode was picked off the list.

    A movie is its own record, so an id said to be a movie's is the movie and is
    read in from that alone, whatever title the show is linked to. A series
    numbers its episodes apart from the series itself, so an episode's id names
    no title to read in and the title the show is linked to is all there is to
    go on.

    Imported here rather than at the top of the module because the TMDB plugin
    is built on the base every plugin is, which reads this module in turn.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    tmdb = TMDB(session)
    if media_type is MediaType.movie:
        tmdb.import_title(MediaType.movie, tmdb_episode_id)
        return

    canonical_show = episode.season.show.canonical_show
    linked = parse_tmdb_key(canonical_show.key, SHOW_LEVEL) if canonical_show else None
    if linked is None:
        return

    linked_media_type, linked_tmdb_id = linked
    tmdb.import_title(linked_media_type, linked_tmdb_id)


# TODO: Validate
def _unlink_others_sharing(
    session: Session,
    episode: Episode,
    canonical_episode_id: uuid.UUID,
) -> None:
    """Take the episode off the other copies of the same title.

    Two websites' episodes pointing at one record is what makes them a single
    episode to watch, so only the title's own other episodes are a clash. A
    `User` saying which episode the record is has settled which one it is, so
    whichever was on it by a guess comes off and is left for `reconcile_show` to
    give a row of its own.

    An episode another `User` decision put there is left where it is, since one
    decision is no reason to undo another.
    """
    statement = (
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            Season.show_id == episode.season.show_id,
            Episode.canonical_episode_id == canonical_episode_id,
            Episode.id != episode.id,
            col(Episode.deleted_at).is_(None),
        )
    )
    for other in session.exec(statement).all():
        if other.canonical_episode_locked and (
            other.canonical_episode_note in MANUAL_NOTES
        ):
            continue

        removed = (
            f"Removed {canonical_episode_id}, which was given to another "
            "episode by hand"
        )
        previous = other.canonical_episode_note
        other.canonical_episode_note = (
            f"{removed}. {previous}" if previous else removed
        )
        other.canonical_episode_id = None
        other.canonical_episode_locked = False
        session.add(other)
        # Left pointing at nothing, so it is given a row standing only for
        # itself rather than left as a copy of nothing at all.
        session.flush()
        point_episode_at(
            session,
            other,
            standalone_episode(session, other, other.season.canonical_season),
        )


# TODO: Validate
def confirm_no_tmdb_match(session: Session, episode: Episode) -> Episode:
    """Hold `episode` as a copy of nothing but itself.

    An episode TMDB has no counterpart for is as settled as one that was linked,
    so the row it already stands for is locked rather than replaced. That is
    what keeps the next import from guessing at it again and what takes it off
    the list of episodes still waiting on somebody.
    """
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = NO_MATCH_NOTE
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode
