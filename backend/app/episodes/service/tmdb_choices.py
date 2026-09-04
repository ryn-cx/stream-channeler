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

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.canonical_media.episodes import canonical_episode_link, links_of
from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    tmdb_id_of,
    tmdb_key_clause,
)
from app.episodes.models import (
    Episode,
)
from app.episodes.name_matching import (
    similarity,
)
from app.episodes.schemas import (
    EpisodeRecord,
    TmdbEpisodeChoice,
)
from app.episodes.service.numbering import (
    _Candidate,
    _candidate_absolute_numbers,
    _candidates_by_show,
    _choice,
    _episode_text,
    _order,
)
from app.episodes.service.records import _record_fields
from app.episodes.text_matching import TextMatcher
from app.seasons.models import Season
from app.shows.models import Show


# TODO: Validate
def _tmdb_ids_used_by_shows(
    session: Session,
    show_ids: set[uuid.UUID],
    /,
) -> dict[uuid.UUID, dict[int, list[EpisodeRecord]]]:
    """Return the episodes of each show using each TMDB episode already.

    Only the show an episode belongs to is read, since another website's non-canonical
    row of the same title has its own episodes pointing at the same TMDB ones and says
    nothing about which of them this show still has going spare.

    Every show of a page at once, rather than one query per episode: a page of
    episodes of the same show asks the same question twenty times over. The
    episode doing the using is named, so a caller working on one of them can
    leave it out of its own answer.
    """
    if not show_ids:
        return {}

    canonical_episode = aliased(Episode)
    canonical_link = canonical_episode_link()
    statement = (
        select(Season.show_id, canonical_episode.key, Episode, Season, Show)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(canonical_link, links_of(Episode, canonical_link))
        .join(
            canonical_episode,
            onclause=col(canonical_link.canonical_episode_id) == canonical_episode.id,
        )
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            is_canonical(canonical_episode),
            col(Season.show_id).in_(show_ids),
            tmdb_key_clause(col(canonical_episode.key)),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    using: dict[uuid.UUID, dict[int, list[EpisodeRecord]]] = defaultdict(
        lambda: defaultdict(list),
    )
    for show_id, key, used_by, season, show in session.exec(statement).all():
        tmdb_id = tmdb_id_of(key, EPISODE_LEVEL)
        if tmdb_id is None:
            continue
        using[show_id][tmdb_id].append(
            EpisodeRecord(**_record_fields(used_by, season, show)),
        )
    return using


# TODO: Validate
def _tmdb_ids_used_by_show(
    session: Session,
    episode: Episode,
) -> dict[int, list[EpisodeRecord]]:
    """Return the episodes of `episode`'s show using each TMDB episode already.

    The episode being linked is left out so the record it already points at is
    not counted as somebody else's.
    """
    show_id = episode.season.show_id
    return {
        tmdb_id: [entry for entry in entries if entry.episode.id != episode.id]
        for tmdb_id, entries in _tmdb_ids_used_by_shows(session, {show_id})
        .get(show_id, {})
        .items()
    }


# TODO: Validate
def _imported_title(session: Session, tmdb_show_id: int) -> uuid.UUID:
    """Read a TMDB series in and return the title its episodes are under."""
    from plugins.TMDB import TMDB  # noqa: PLC0415

    return TMDB(session).import_show(tmdb_show_id).id


# TODO: Validate
def list_tmdb_episode_choices(
    session: Session,
    episode: Episode,
    tmdb_show_id: int | None = None,
    name: str | None = None,
    limit: int = 100,
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
    if name and name.strip():
        return _named_tmdb_episode_choices(session, episode, name.strip(), limit)

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
    show_ids = set(canonical_show_ids)
    choices = _title_choices(session, episode, titles, show_ids)
    named = {choice.episode.id for choice in choices}
    choices += [
        choice
        for choice in _matched_choices(
            session,
            episode,
            _similar_canonical_episodes(session, episode.name, 25),
            show_ids,
        )
        if choice.episode.id not in named
    ]
    return sorted(
        choices,
        key=lambda choice: _order(
            choice.season.season_number,
            choice.episode.episode_number,
        ),
    )


# TODO: Validate
def _named_canonical_episodes(
    session: Session,
    wanted: str,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    statement = (
        select(Episode.id, Season.show_id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            is_canonical(Episode),
            is_canonical(Show),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
            tmdb_key_clause(col(Episode.key)),
            col(Episode.name).icontains(wanted, autoescape=True),
        )
        .order_by(col(Episode.name), col(Episode.id))
        .limit(limit)
    )
    return [
        (episode_id, show_id) for episode_id, show_id in session.exec(statement).all()
    ]


# TODO: Validate
def _similar_canonical_episodes(
    session: Session,
    name: str | None,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    if not name:
        return []

    statement = (
        select(Episode.id, Season.show_id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            is_canonical(Episode),
            is_canonical(Show),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
            tmdb_key_clause(col(Episode.key)),
            col(Episode.name).is_not(None),
            col(Episode.name).op("%")(name),
        )
        .order_by(col(Episode.name).op("<->")(name))
        .limit(limit)
    )
    return [
        (episode_id, show_id) for episode_id, show_id in session.exec(statement).all()
    ]


# TODO: Validate
def _title_choices(
    session: Session,
    episode: Episode,
    titles: list[list[_Candidate]],
    show_ids: set[uuid.UUID],
    keep: set[uuid.UUID] | None = None,
) -> list[TmdbEpisodeChoice]:
    used_tmdb_ids = _tmdb_ids_used_by_show(session, episode)
    choices: list[TmdbEpisodeChoice] = []
    for title in titles:
        numbers = _candidate_absolute_numbers(title)
        for candidate in title:
            if keep is not None and candidate[0].id not in keep:
                continue
            choice = _choice(
                candidate,
                numbers,
                similarity(episode.name, candidate[0].name),
            )
            if choice is None:
                continue
            choice.from_show = choice.show.id in show_ids
            choice.used_by = used_tmdb_ids.get(choice.episode.tmdb_id or 0, [])
            choice.already_used = bool(choice.used_by)
            choices.append(choice)
    return choices


# TODO: Validate
def _matched_choices(
    session: Session,
    episode: Episode,
    matches: list[tuple[uuid.UUID, uuid.UUID]],
    show_ids: set[uuid.UUID],
) -> list[TmdbEpisodeChoice]:
    if not matches:
        return []

    by_title = _candidates_by_show(session, {show_id for _id, show_id in matches})
    return _title_choices(
        session,
        episode,
        list(by_title.values()),
        show_ids,
        {episode_id for episode_id, _show_id in matches},
    )


# TODO: Validate
def _blended_name_scored(
    episode: Episode,
    choices: list[TmdbEpisodeChoice],
) -> list[TmdbEpisodeChoice]:
    own_name = _episode_text(episode, titles=True)
    named = [choice for choice in choices if (choice.episode.name or "").strip()]
    if not own_name or not named:
        return choices

    matcher = TextMatcher([(choice.episode.name or "").strip() for choice in named])
    for choice, score in zip(named, matcher.blended_scores(own_name), strict=True):
        choice.similarity = score
    return choices


# TODO: Validate
def _named_tmdb_episode_choices(
    session: Session,
    episode: Episode,
    wanted: str,
    limit: int,
) -> list[TmdbEpisodeChoice]:
    choices = _blended_name_scored(
        episode,
        _matched_choices(
            session,
            episode,
            _named_canonical_episodes(session, wanted, limit),
            set(episode.season.show.canonical_show_ids),
        ),
    )
    return sorted(choices, key=lambda choice: -choice.similarity)
