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
from typing import Any

from sqlalchemy.orm import aliased, contains_eager
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import canonical_episode_link, links_of
from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    tmdb_id_of,
    tmdb_key_clause,
)
from app.canonical_media.metadata import (
    tmdb_episode_url,
    tmdb_season_url,
    tmdb_show_url,
)
from app.episodes.models import (
    Episode,
    EpisodeCanonicalEpisode,
)
from app.episodes.name_matching import plaintext, similarity
from app.episodes.schemas import (
    DuplicatedCanonicalEpisodeOutput,
    DuplicatedLinkEpisodeOutput,
    EpisodeUsingTmdb,
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
    UnmatchedEpisodesPublic,
)
from app.media.media_type import MediaType
from app.plugins.identifiers import TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.service import _apply_filter_options, _apply_sort_options
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
    return similarity(episode.name, candidate_episode.name), numbering_matches


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
                similarity(episode.name, candidate[0].name),
            )
    return None


# TODO: Validate
def _has_tmdb_title() -> ColumnElement[bool]:
    """Whether TMDB holds any of the titles the outer `Show` is linked to.

    Any of them rather than one picked out of them, since a listing that mixes
    titles is as much linked to the second as of the first and an episode of
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
# Which joined column each sortable name is, since a name a non-canonical row is not
# sorted by on its own row - the show it is under, the source that carries it - has no
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

    Every title a listing is linked to contributes its episodes, since a listing
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
    used = _tmdb_ids_used_by_shows(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    return [
        UnmatchedEpisodeOutput(
            id=episode.id,
            canonical_episode_id=episode.sole_canonical_episode_id,
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
            best_match=_marked_used(
                _best_match(
                    episode,
                    season,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                ),
                episode.id,
                used.get(show.id, {}),
            ),
            number_match=_marked_used(
                _number_match(
                    episode,
                    season,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                    source_numbers.get(episode.id),
                ),
                episode.id,
                used.get(show.id, {}),
            ),
        )
        for episode, season, show, source in rows
    ]


# TODO: Validate
def _marked_used(
    choice: TmdbEpisodeChoice | None,
    episode_id: uuid.UUID,
    used: dict[int, list[EpisodeUsingTmdb]],
) -> TmdbEpisodeChoice | None:
    """Say which of the show's other episodes already point at `choice`.

    Suggested to one episode and taken by another is what a suggestion worth
    doubting looks like, since two episodes of one listing are rarely the same
    TMDB episode. The episode being suggested to is left out, as an episode
    already pointing at what it is being offered is not competing with itself.
    """
    if choice is None:
        return None
    choice.used_by = [
        entry
        for entry in used.get(choice.tmdb_episode_id, [])
        if entry.id != episode_id
    ]
    choice.already_used = bool(choice.used_by)
    return choice


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
                canonical_episode_id=episode.sole_canonical_episode_id,
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
                    and plaintext(episode.name)
                    and plaintext(episode.name) == plaintext(best_match.name),
                ),
            ),
        )
    return outputs


# TODO: Validate
def _tmdb_ids_used_by_shows(
    session: Session,
    show_ids: set[uuid.UUID],
    /,
) -> dict[uuid.UUID, dict[int, list[EpisodeUsingTmdb]]]:
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
        select(Season.show_id, canonical_episode.key, Episode, Season)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(canonical_link, links_of(Episode, canonical_link))
        .join(
            canonical_episode,
            onclause=col(canonical_link.canonical_episode_id) == canonical_episode.id,
        )
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(canonical_episode),
            col(Season.show_id).in_(show_ids),
            tmdb_key_clause(col(canonical_episode.key)),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
        )
    )
    using: dict[uuid.UUID, dict[int, list[EpisodeUsingTmdb]]] = defaultdict(
        lambda: defaultdict(list),
    )
    for show_id, key, used_by, season in session.exec(statement).all():
        tmdb_id = tmdb_id_of(key, EPISODE_LEVEL)
        if tmdb_id is None:
            continue
        using[show_id][tmdb_id].append(
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
def _tmdb_ids_used_by_show(
    session: Session,
    episode: Episode,
) -> dict[int, list[EpisodeUsingTmdb]]:
    """Return the episodes of `episode`'s show using each TMDB episode already.

    The episode being linked is left out so the record it already points at is
    not counted as somebody else's.
    """
    show_id = episode.season.show_id
    return {
        tmdb_id: [entry for entry in entries if entry.id != episode.id]
        for tmdb_id, entries in _tmdb_ids_used_by_shows(session, {show_id})
        .get(show_id, {})
        .items()
    }


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
                similarity(episode.name, candidate[0].name),
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
def _duplicated_link_pairs(
    session: Session,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    uses = func.count(col(EpisodeCanonicalEpisode.episode_id).distinct())
    unsettled = func.bool_or(col(Episode.canonical_episode_locked).is_(False))
    statement = (
        select(
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
        )
        .join(Episode, onclause=col(EpisodeCanonicalEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .group_by(
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
        )
        .having(uses > 1, unsettled)
        .limit(limit)
    )
    return [
        (canonical_id, source_id)
        for canonical_id, source_id in session.exec(statement).all()
    ]


# TODO: Validate
def _episodes_linking_to(
    session: Session,
    pairs: Collection[tuple[uuid.UUID, uuid.UUID]],
) -> dict[tuple[uuid.UUID, uuid.UUID], list[DuplicatedLinkEpisodeOutput]]:
    canonical_episode_ids = {canonical_id for canonical_id, _source_id in pairs}
    statement = (
        select(
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
            Episode,
            Season,
        )
        .join(Episode, onclause=col(EpisodeCanonicalEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            col(EpisodeCanonicalEpisode.canonical_episode_id).in_(
                canonical_episode_ids,
            ),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(col(Season.season_number), col(Episode.episode_number))
    )
    wanted = set(pairs)
    linking: dict[
        tuple[uuid.UUID, uuid.UUID],
        list[DuplicatedLinkEpisodeOutput],
    ] = defaultdict(list)
    for canonical_id, source_id, episode, season in session.exec(statement).all():
        if (canonical_id, source_id) not in wanted:
            continue
        output = DuplicatedLinkEpisodeOutput.model_validate(episode)
        output.season_number = season.season_number
        linking[canonical_id, source_id].append(output)
    return linking


# TODO: Validate
def get_duplicated_canonical_episodes(
    session: Session,
    limit: int,
) -> list[DuplicatedCanonicalEpisodeOutput]:
    """Return every canonical episode a single source points more than one episode at.

    Two episodes of one website standing for the same canonical episode is a
    link made wrongly rather than a title carried twice, so they are gathered by
    the canonical episode they collide on and served with the episodes that made
    the claim. Any provider's canonical rows are read, not only TMDB's.
    """
    pairs = _duplicated_link_pairs(session, limit)
    if not pairs:
        return []

    linking = _episodes_linking_to(session, pairs)
    canonical_episodes = {
        episode.id: (episode, season, show, source)
        for episode, season, show, source in session.exec(
            select(Episode, Season, Show, Source)
            .join(Season, onclause=col(Episode.season_id) == Season.id)
            .join(Show, onclause=col(Season.show_id) == Show.id)
            .join(Source, onclause=col(Show.source_id) == Source.id)
            .where(col(Episode.id).in_({canonical_id for canonical_id, _ in pairs})),
        ).all()
    }
    sources = {
        source.id: source
        for source in session.exec(
            select(Source).where(
                col(Source.id).in_({source_id for _, source_id in pairs}),
            ),
        ).all()
    }

    outputs: list[DuplicatedCanonicalEpisodeOutput] = []
    for canonical_id, source_id in pairs:
        found = canonical_episodes.get(canonical_id)
        source = sources.get(source_id)
        if found is None or source is None:
            continue
        episode, season, show, canonical_source = found
        outputs.append(
            DuplicatedCanonicalEpisodeOutput(
                id=f"{episode.id}:{source.id}",
                canonical_episode_id=episode.id,
                season_id=season.id,
                show_id=show.id,
                key=episode.key,
                name=episode.name,
                season_number=season.season_number,
                episode_number=episode.episode_number,
                show_name=show.name,
                show_year=show.year,
                url=tmdb_episode_url(
                    show.key,
                    season.season_number,
                    episode.episode_number,
                )
                or episode.url,
                show_url=tmdb_show_url(show.key) or show.url,
                canonical_source_name=canonical_source.name,
                canonical_plugin_name=canonical_source.plugin.name,
                source_id=source.id,
                source_name=source.name,
                plugin_name=source.plugin.name,
                linked_episodes=linking.get((canonical_id, source_id), []),
            ),
        )
    return sorted(
        outputs,
        key=lambda output: (
            output.source_name or "",
            output.show_name or "",
            output.season_number or 0,
            output.episode_number or 0,
        ),
    )
