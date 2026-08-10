# TODO: Validate
"""Episodes no TMDB record was found for, each beside the closest TMDB episode.

An import points an episode at TMDB by name, and an episode whose name matched
nothing keeps the identifier its own website issued. Those are what is gathered
here, each paired with the TMDB episode that came closest, so the link a name
could not make can be made by hand instead.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from difflib import SequenceMatcher

from fastapi import HTTPException
from sqlmodel import Session, col, select

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
from app.media.identifiers import (
    TMDB_IDENTIFIER_PREFIX,
    TMDB_PLUGIN_KEY,
    parse_tmdb_identifier,
    tmdb_identifier,
)
from app.media.media_type import MediaType
from app.media.tmdb_fallback import tmdb_episode_url
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

_TMDB_IDENTIFIER_PATTERN = f"{TMDB_IDENTIFIER_PREFIX}%"
# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")

type _Candidate = tuple[Episode, Season, Show]
type Numbering = tuple[uuid.UUID, int | None, int | None]


def _order(
    season_number: int | None,
    episode_number: int | None,
) -> tuple[float, float]:
    return (
        _UNNUMBERED if season_number is None else season_number,
        _UNNUMBERED if episode_number is None else episode_number,
    )


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


def _plaintext(name: str | None) -> str:
    if not name:
        return ""
    return "".join(character for character in name.casefold() if character.isalnum())


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


def _candidate_absolute_numbers(candidates: list[_Candidate]) -> dict[uuid.UUID, int]:
    return absolute_numbers(
        [
            (episode.id, season.season_number, episode.episode_number)
            for episode, season, _show in candidates
        ],
    )


def _choice(
    candidate: _Candidate,
    absolute_numbers: dict[uuid.UUID, int],
    similarity: float,
) -> TmdbEpisodeChoice | None:
    episode, season, show = candidate
    if episode.tmdb_id is None:
        return None

    return TmdbEpisodeChoice(
        tmdb_episode_id=episode.tmdb_id,
        name=episode.name,
        season_number=season.season_number,
        episode_number=episode.episode_number,
        absolute_number=absolute_numbers.get(episode.id),
        url=tmdb_episode_url(show.key, season.season_number, episode.episode_number),
        similarity=similarity,
    )


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
        .where(
            Plugin.key != TMDB_PLUGIN_KEY,
            col(Episode.episode_identifier).not_like(_TMDB_IDENTIFIER_PATTERN),
            # A locked identifier is one a `User` has already settled, whether by
            # pointing the episode at a TMDB record or by saying there is none to
            # point it at, so it is no longer waiting on anybody.
            col(Episode.episode_identifier_locked).is_(False),
            col(Show.show_identifier).like(_TMDB_IDENTIFIER_PATTERN),
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


def _candidates_by_show(
    session: Session,
    show_identifiers: set[str],
) -> dict[str, list[_Candidate]]:
    """Return every TMDB episode of each linked title, keyed by the title's identifier.

    A title's episodes are read once for the whole page rather than once per
    episode, since every episode of the same title is compared against the same
    list.
    """
    if not show_identifiers:
        return {}

    statement = (
        select(Episode, Season, Show)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Show.show_identifier).in_(show_identifiers),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    candidates: dict[str, list[_Candidate]] = defaultdict(list)
    for episode, season, show in session.exec(statement).all():
        candidates[show.show_identifier].append((episode, season, show))
    return candidates


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


def list_unmatched_episodes(
    session: Session,
    limit: int,
) -> list[UnmatchedEpisodeOutput]:
    """Return the episodes still carrying their own website's identifier.

    Only episodes of a title that is itself linked are listed, since a title with
    no TMDB counterpart has no episodes to be matched against and nothing to
    choose from.
    """
    rows = _unmatched_rows(session, limit)
    candidates = _candidates_by_show(
        session,
        {show.show_identifier for _episode, _season, show, _source in rows},
    )
    candidate_numbers = {
        show_identifier: _candidate_absolute_numbers(show_candidates)
        for show_identifier, show_candidates in candidates.items()
    }
    source_numbers = _source_absolute_numbers(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    return [
        UnmatchedEpisodeOutput(
            id=episode.id,
            episode_identifier=episode.episode_identifier,
            episode_identifier_note=episode.episode_identifier_note,
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
                candidates.get(show.show_identifier, []),
                candidate_numbers.get(show.show_identifier, {}),
            ),
        )
        for episode, season, show, source in rows
    ]


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
            col(Episode.episode_identifier_locked).is_(False),
            col(Show.show_identifier).like(_TMDB_IDENTIFIER_PATTERN),
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
        {show.show_identifier for _episode, _season, show, _source in rows},
    )
    candidate_numbers = {
        show_identifier: _candidate_absolute_numbers(show_candidates)
        for show_identifier, show_candidates in candidates.items()
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
            candidates.get(show.show_identifier, []),
            candidate_numbers.get(show.show_identifier, {}),
        )
        outputs.append(
            UnlockedEpisodeOutput(
                id=episode.id,
                episode_identifier=episode.episode_identifier,
                episode_identifier_note=episode.episode_identifier_note,
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


def _identifiers_used_by_show(session: Session, episode: Episode) -> set[str]:
    """Return the TMDB identifiers the rest of `episode`'s show already points at.

    Only the show the episode belongs to is read, since another website's copy
    of the same title has its own episodes pointing at the same TMDB ones and
    says nothing about which of them this show still has going spare. The
    episode being linked is left out so the record it already points at is not
    counted as somebody else's.
    """
    statement = (
        select(Episode.episode_identifier)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            Season.show_id == episode.season.show_id,
            col(Episode.id) != episode.id,
            col(Episode.episode_identifier).like(_TMDB_IDENTIFIER_PATTERN),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    return set(session.exec(statement).all())


def _imported_title_identifier(session: Session, tmdb_show_id: int) -> str:
    """Read a TMDB series in and return the identifier its episodes are under.

    Read in rather than looked for, since a title nothing has imported has no
    episodes stored to choose from and naming it is the asking for it.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    if TMDB(session).import_title(MediaType.tv, tmdb_show_id) is None:
        raise HTTPException(
            status_code=400,
            detail=f"TMDB has no series with the id {tmdb_show_id}",
        )
    return tmdb_identifier(MediaType.tv, tmdb_show_id)


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
    show_identifier = (
        episode.season.show.show_identifier
        if tmdb_show_id is None
        else _imported_title_identifier(session, tmdb_show_id)
    )
    candidates = _candidates_by_show(session, {show_identifier}).get(
        show_identifier,
        [],
    )
    absolute_numbers = _candidate_absolute_numbers(candidates)
    used_identifiers = _identifiers_used_by_show(session, episode)
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
        choice.already_used = (
            tmdb_identifier(MediaType.tv, choice.tmdb_episode_id) in used_identifiers
        )
    return sorted(
        choices,
        key=lambda choice: _order(choice.season_number, choice.episode_number),
    )


def _tmdb_episode_identifiers(
    tmdb_episode_id: int,
    media_type: MediaType | None,
) -> set[str]:
    """Return the identifiers an id could be, given what is known of its half."""
    if media_type is not None:
        return {tmdb_identifier(media_type, tmdb_episode_id)}
    return {tmdb_identifier(half, tmdb_episode_id) for half in MediaType}


def _tmdb_episode(
    session: Session,
    tmdb_episode_id: int,
    media_type: MediaType | None = None,
) -> Episode | None:
    """Return the imported TMDB episode an id names, in one half of the catalogue.

    An id said to be a movie's is only ever looked for as a movie, so a series
    episode that happens to carry the same number is never taken for it, and the
    other way about. An id with neither said of it is looked for as both, which
    is what a choice taken off the list is.
    """
    identifiers = _tmdb_episode_identifiers(tmdb_episode_id, media_type)
    statement = (
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            col(Episode.episode_identifier).in_(identifiers),
            col(Episode.deleted_at).is_(None),
        )
    )
    return session.exec(statement).first()


def link_episode(
    session: Session,
    episode: Episode,
    tmdb_episode_id: int,
    *,
    media_type: MediaType | None = None,
    selected: bool = False,
) -> Episode:
    """Point `episode` at a TMDB episode a `User` chose, and hold it there.

    The identifier is taken off the imported TMDB episode rather than built from
    the id given, so an id TMDB has nothing imported for is refused instead of
    stored as a link to a record that will never fill anything in. The link is
    locked, which is what keeps the next import's own guess from replacing it.

    `selected` says the `User` went and found the episode rather than taking the
    one they were shown, which is the note the link is left with.
    """
    _import_named_media(session, episode, tmdb_episode_id, media_type)

    counterpart = _tmdb_episode(session, tmdb_episode_id, media_type)
    if counterpart is None:
        looked_for = " or ".join(
            sorted(_tmdb_episode_identifiers(tmdb_episode_id, media_type)),
        )
        raise HTTPException(
            status_code=404,
            detail=f"TMDB has no imported episode that is {looked_for}",
        )

    _unlink_others_sharing(session, episode, counterpart.episode_identifier)

    episode.episode_identifier = counterpart.episode_identifier
    episode.episode_identifier_locked = True
    episode.episode_identifier_note = (
        MANUALLY_SELECTED_NOTE if selected else MANUALLY_CONFIRMED_NOTE
    )
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


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

    linked = parse_tmdb_identifier(episode.season.show.show_identifier)
    if linked is None:
        return

    linked_media_type, linked_tmdb_id = linked
    tmdb.import_title(linked_media_type, linked_tmdb_id)


def _unlink_others_sharing(
    session: Session,
    episode: Episode,
    identifier: str,
) -> None:
    """Take `identifier` off the other episodes of the same copy of the title.

    Two websites' episodes carrying one identifier is what makes them a single
    episode to watch, so only the title's own other episodes are a clash. A
    `User` saying which episode the record is has settled which one it is, so
    whichever was on it by a guess comes off and goes back to the identifier its
    own website issued.

    An episode another `User` decision put there is left where it is, since one
    decision is no reason to undo another.
    """
    statement = (
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            Season.show_id == episode.season.show_id,
            Episode.episode_identifier == identifier,
            Episode.id != episode.id,
            col(Episode.deleted_at).is_(None),
        )
    )
    for other in session.exec(statement).all():
        if other.episode_identifier_locked and (
            other.episode_identifier_note in MANUAL_NOTES
        ):
            continue

        plugin_key = other.season.show.source.plugin.key
        removed = f"Removed {identifier}, which was given to another episode by hand"
        previous = other.episode_identifier_note
        other.episode_identifier_note = (
            f"{removed}. {previous}" if previous else removed
        )
        other.episode_identifier = f"{plugin_key} {other.key}"
        other.episode_identifier_locked = False
        session.add(other)


def confirm_no_tmdb_match(session: Session, episode: Episode) -> Episode:
    """Hold `episode` at the identifier its own website issued.

    An episode TMDB has no counterpart for is as settled as one that was linked,
    so the identifier it already carries is locked rather than replaced. That is
    what keeps the next import from guessing at it again and what takes it off
    the list of episodes still waiting on somebody.
    """
    episode.episode_identifier_locked = True
    episode.episode_identifier_note = NO_MATCH_NOTE
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode
