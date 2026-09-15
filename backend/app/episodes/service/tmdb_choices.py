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
    _candidates_by_title,
    _choice,
    _episode_text,
    _order,
)
from app.episodes.service.records import _record_fields
from app.episodes.text_matching import TextMatcher
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.episodes import links_of, tmdb_episode_link
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import (
    get_tmdb_id,
    tmdb_key_clause,
)


# TODO: Validate
def _tmdb_ids_used_by_titles(
    session: Session,
    title_ids: set[uuid.UUID],
    /,
) -> dict[uuid.UUID, dict[int, list[EpisodeRecord]]]:
    """Return the episodes of each title using each TMDB episode already.

    Only the title an episode belongs to is read, since another website's non-canonical
    row of the same title has its own episodes pointing at the same TMDB ones and says
    nothing about which of them this title still has going spare.

    Every title of a page at once, rather than one query per episode: a page of
    episodes of the same title asks the same question twenty times over. The
    episode doing the using is named, so a caller working on one of them can
    leave it out of its own answer.
    """
    if not title_ids:
        return {}

    tmdb_episode = aliased(Episode)
    tmdb_link = tmdb_episode_link()
    statement = (
        select(Season.title_id, tmdb_episode.key, Episode, Season, Title)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(tmdb_link, links_of(Episode, tmdb_link))
        .join(
            tmdb_episode,
            onclause=col(tmdb_link.tmdb_episode_id) == tmdb_episode.id,
        )
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            is_not_linked(tmdb_episode),
            col(Season.title_id).in_(title_ids),
            tmdb_key_clause(col(tmdb_episode.key)),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    using: dict[uuid.UUID, dict[int, list[EpisodeRecord]]] = defaultdict(
        lambda: defaultdict(list),
    )
    for title_id, key, used_by, season, title in session.exec(statement).all():
        tmdb_id = get_tmdb_id(key)
        using[title_id][tmdb_id].append(
            EpisodeRecord(**_record_fields(used_by, season, title)),
        )
    return using


# TODO: Validate
def _tmdb_ids_used_by_title(
    session: Session,
    episode: Episode,
) -> dict[int, list[EpisodeRecord]]:
    """Return the episodes of `episode`'s title using each TMDB episode already.

    The episode being linked is left out so the record it already points at is
    not counted as somebody else's.
    """
    title_id = episode.season.title_id
    return {
        tmdb_id: [entry for entry in entries if entry.episode.id != episode.id]
        for tmdb_id, entries in _tmdb_ids_used_by_titles(session, {title_id})
        .get(title_id, {})
        .items()
    }


# TODO: Validate
def list_tmdb_episode_choices(
    session: Session,
    episode_to_link: Episode,
    search_string: str | None = None,
    limit: int = 100,
) -> list[TmdbEpisodeChoice]:
    already_linked = set(episode_to_link.tmdb_episode_ids)
    # If a search string is included the user is searching for an episode that can
    # belong to anny title.
    if search_string and search_string.strip():
        return [
            choice
            for choice in _named_tmdb_episode_choices(
                session,
                episode_to_link,
                search_string.strip(),
                limit,
            )
            if choice.episode.id not in already_linked
        ]

    tmdb_title_ids = episode_to_link.season.title.tmdb_title_ids
    if not tmdb_title_ids:
        return []
    unique_tmdb_title_ids = set(tmdb_title_ids)
    by_title = _candidates_by_title(session, unique_tmdb_title_ids)
    titles = [by_title.get(tmdb_title_id, []) for tmdb_title_id in tmdb_title_ids]
    choices = _title_choices(session, episode_to_link, titles, unique_tmdb_title_ids)
    named = {choice.episode.id for choice in choices}
    choices += [
        choice
        for choice in _matched_choices(
            session,
            episode_to_link,
            _similar_tmdb_episodes(session, episode_to_link.name, 25),
            unique_tmdb_title_ids,
        )
        if choice.episode.id not in named
    ]
    return sorted(
        (choice for choice in choices if choice.episode.id not in already_linked),
        key=lambda choice: _order(
            choice.season.season_number,
            choice.episode.episode_number,
        ),
    )


# TODO: Validate
def _named_tmdb_episodes(
    session: Session,
    search_string: str,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    statement = (
        select(Episode.id, Season.title_id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            is_not_linked(Episode),
            is_not_linked(Title),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
            tmdb_key_clause(col(Episode.key)),
            col(Episode.name).icontains(search_string, autoescape=True),
        )
        .order_by(col(Episode.name), col(Episode.id))
        .limit(limit)
    )
    return [
        (tmdb_episode_id, tmdb_title_id)
        for tmdb_episode_id, tmdb_title_id in session.exec(statement).all()
    ]


# TODO: Validate
def _similar_tmdb_episodes(
    session: Session,
    name: str | None,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    if not name:
        return []

    statement = (
        select(Episode.id, Season.title_id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            is_not_linked(Episode),
            is_not_linked(Title),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
            tmdb_key_clause(col(Episode.key)),
            col(Episode.name).is_not(None),
            col(Episode.name).op("%")(name),
        )
        .order_by(col(Episode.name).op("<->")(name))
        .limit(limit)
    )
    return [
        (tmdb_episode_id, tmdb_title_id)
        for tmdb_episode_id, tmdb_title_id in session.exec(statement).all()
    ]


# TODO: Validate
def _title_choices(
    session: Session,
    episode: Episode,
    titles: list[list[_Candidate]],
    tmdb_title_ids: set[uuid.UUID],
    keep_tmdb_episode_ids: set[uuid.UUID] | None = None,
) -> list[TmdbEpisodeChoice]:
    used_tmdb_ids = _tmdb_ids_used_by_title(session, episode)
    choices: list[TmdbEpisodeChoice] = []
    for title in titles:
        numbers = _candidate_absolute_numbers(title)
        for candidate in title:
            if (
                keep_tmdb_episode_ids is not None
                and candidate[0].id not in keep_tmdb_episode_ids
            ):
                continue
            choice = _choice(
                candidate,
                numbers,
                similarity(episode.name, candidate[0].name),
            )
            if choice is None:
                continue
            choice.from_title = choice.title.id in tmdb_title_ids
            choice.used_by = used_tmdb_ids.get(choice.episode.tmdb_id or 0, [])
            choice.already_used = bool(choice.used_by)
            choices.append(choice)
    return choices


# TODO: Validate
def _matched_choices(
    session: Session,
    episode: Episode,
    tmdb_matches: list[tuple[uuid.UUID, uuid.UUID]],
    tmdb_title_ids: set[uuid.UUID],
) -> list[TmdbEpisodeChoice]:
    if not tmdb_matches:
        return []

    by_title = _candidates_by_title(
        session,
        {tmdb_title_id for _episode_id, tmdb_title_id in tmdb_matches},
    )
    return _title_choices(
        session,
        episode,
        list(by_title.values()),
        tmdb_title_ids,
        {tmdb_episode_id for tmdb_episode_id, _title_id in tmdb_matches},
    )


# TODO: Validate
def _blended_name_scored(
    episode_to_link: Episode,
    choices: list[TmdbEpisodeChoice],
) -> list[TmdbEpisodeChoice]:
    own_name = _episode_text(episode_to_link, titles=True)
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
    episode_to_link: Episode,
    search_string: str,
    limit: int,
) -> list[TmdbEpisodeChoice]:
    choices = _blended_name_scored(
        episode_to_link=episode_to_link,
        choices=_matched_choices(
            session=session,
            episode=episode_to_link,
            tmdb_matches=_named_tmdb_episodes(session, search_string, limit),
            tmdb_title_ids=set(episode_to_link.season.title.tmdb_title_ids),
        ),
    )
    return sorted(choices, key=lambda choice: -choice.similarity)
