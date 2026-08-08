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
type _Numbering = tuple[uuid.UUID, int | None, int | None]


def _order(
    season_number: int | None,
    episode_number: int | None,
) -> tuple[float, float]:
    return (
        _UNNUMBERED if season_number is None else season_number,
        _UNNUMBERED if episode_number is None else episode_number,
    )


def _absolute_numbers(numberings: Sequence[_Numbering]) -> dict[uuid.UUID, int]:
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
    absolute_numbers: dict[uuid.UUID, int] = {}
    for record_id, season_number, _episode_number in ordered:
        if not season_number:
            continue
        absolute_numbers[record_id] = len(absolute_numbers) + 1
    return absolute_numbers


def _plaintext(name: str | None) -> str:
    if not name:
        return ""
    return "".join(character for character in name.casefold() if character.isalnum())


def _similarity(name: str | None, other_name: str | None) -> float:
    plaintext = _plaintext(name)
    other_plaintext = _plaintext(other_name)
    if not plaintext or not other_plaintext:
        return 0.0
    if plaintext in other_plaintext or other_plaintext in plaintext:
        return 1.0
    return SequenceMatcher(None, plaintext, other_plaintext).ratio()


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
    return _absolute_numbers(
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
    per_show: dict[uuid.UUID, list[_Numbering]] = defaultdict(list)
    for episode_id, show_id, season_number, episode_number in session.exec(
        statement,
    ).all():
        per_show[show_id].append((episode_id, season_number, episode_number))

    absolute_numbers: dict[uuid.UUID, int] = {}
    for numberings in per_show.values():
        absolute_numbers |= _absolute_numbers(numberings)
    return absolute_numbers


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
            name=episode.name,
            episode_number=episode.episode_number,
            absolute_number=source_numbers.get(episode.id),
            season_name=season.name,
            season_number=season.season_number,
            show_name=show.name,
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
                name=episode.name,
                episode_number=episode.episode_number,
                absolute_number=source_numbers.get(episode.id),
                season_name=season.name,
                season_number=season.season_number,
                show_name=show.name,
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


def list_tmdb_episode_choices(
    session: Session,
    episode: Episode,
) -> list[TmdbEpisodeChoice]:
    """Return every TMDB episode of the title `episode` belongs to, in order.

    They are ordered as the title runs rather than as TMDB returns them, so the
    one an episode is meant to be is found by counting through the title the same
    way the website that holds it does. Each carries how much of its name it
    shares with `episode`, which is the other order they are worth reading in.
    """
    show_identifier = episode.season.show.show_identifier
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


def _tmdb_episode(session: Session, tmdb_episode_id: int) -> Episode | None:
    identifiers = {
        tmdb_identifier(media_type, tmdb_episode_id) for media_type in MediaType
    }
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
    counterpart = _tmdb_episode(session, tmdb_episode_id)
    if counterpart is None:
        raise HTTPException(
            status_code=404,
            detail=f"No imported TMDB episode has the id {tmdb_episode_id}",
        )

    episode.episode_identifier = counterpart.episode_identifier
    episode.episode_identifier_locked = True
    episode.episode_identifier_note = (
        MANUALLY_SELECTED_NOTE if selected else MANUALLY_CONFIRMED_NOTE
    )
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


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
