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

from sqlalchemy import nullslast
from sqlalchemy.orm import aliased, contains_eager
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import canonical_episode_link, links_of
from app.canonical_media.filters import is_canonical, is_non_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    tmdb_id_of,
    tmdb_key_clause,
)
from app.canonical_media.metadata import canonical_episode_of, tmdb_episode_url
from app.episodes.models import (
    Episode,
    EpisodeCanonicalEpisode,
)
from app.episodes.name_matching import (
    is_only_numbered_name,
    is_untitled_name,
    plaintext,
    similarity,
)
from app.episodes.schemas import (
    CanonicalEpisodeRecord,
    DuplicatedCanonicalEpisodeOutput,
    EpisodeInformationOutput,
    EpisodeInformationSide,
    EpisodeListOutput,
    EpisodeOutput,
    EpisodeRecord,
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
    UnmatchedEpisodesPublic,
    UnmatchedReadOptions,
    UserEpisodeUrlOutput,
)
from app.episodes.text_matching import TextMatcher
from app.episodes.user_urls import (
    canonical_episode_for_url,
    clear_user_episode_url,
    set_user_episode_url,
    single_canonical_episode_id,
    user_episode_url,
)
from app.issue_reports.service import list_episode_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY, YOUTUBE_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import SortOption
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.service import _apply_filter_options, _apply_sort_options
from app.shows.models import Show, ShowCanonicalShow
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourceListPublic
from app.users.models import User

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")


# TODO: Validate
def episode_record(episode: Episode) -> EpisodeRecord:
    """Return an `Episode` with the season, the title and the website above it."""
    season = episode.season
    show = season.show
    return EpisodeRecord(**_record_fields(episode, season, show))


# TODO: Validate
def _record_fields(episode: Episode, season: Season, show: Show) -> dict[str, Any]:
    """Return an episode and everything above it, each as the record it is."""
    return {
        "episode": EpisodeOutput.model_validate(episode),
        "season": SeasonOutput.model_validate(season),
        "show": ShowPublic.model_validate(show),
        "source": SourceListPublic.model_validate(show.source),
    }


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
    if tmdb_id_of(episode.key, EPISODE_LEVEL) is None:
        return None

    return TmdbEpisodeChoice(
        **_record_fields(episode, season, show),
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
    for show_id, show_candidates in candidates.items():
        written = [
            candidate
            for candidate in show_candidates
            if _episode_text(candidate[0], titles=titles)
        ]
        if written:
            matchers[show_id] = (
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
        candidate_episode, candidate_season, _show = candidate
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
def _unmatched_base(
    *,
    non_canonical_shows_only: bool = False,
) -> SelectOfScalar[Episode]:
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
            col(Source.key) != "Crunchyroll Music",
            is_canonical(Episode),
            # An episode settled as one TMDB has no record of points at nothing
            # and is locked there, which reads as canonical the same way one
            # nothing has worked out yet does. The lock is what tells them
            # apart, and a settled episode is waiting on nobody.
            col(Episode.canonical_episode_validated_at).is_(None),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
            *([is_non_canonical(Show)] if non_canonical_shows_only else []),
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
        partition_by=col(Season.show_id),
        order_by=(
            col(Season.season_number),
            nullslast(col(Episode.episode_number)),
            col(Episode.id),
        ),
    )


# TODO: Validate
def absolute_numbers_of(
    session: Session,
    show_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Count every episode of each title, and return that count by episode id.

    The whole title is counted rather than only the episodes being listed, since an
    episode's place in a title is decided by how many come before it, which the
    ones left over from a name match say nothing about. Nothing says which rows are
    canonical, so a website's own title and a canonical title are both counted the
    way the title they are counts.
    """
    if not show_ids:
        return {}

    statement = (
        select(Episode.id, _absolute_number_column())
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(col(Season.show_id).in_(show_ids), _counted_episodes())
    )
    return dict(session.exec(statement).all())


# TODO: Validate
def _expanded_sort_options(sort_options: list[SortOption]) -> list[SortOption]:
    expanded: list[SortOption] = []
    for option in sort_options:
        expanded.append(option)
        if option.column == "summary":
            expanded += [
                SortOption(id="source_name", desc=option.desc),
                SortOption(id="season_number", desc=option.desc),
                SortOption(id="episode_number", desc=option.desc),
            ]
    return expanded


# TODO: Validate
def list_unmatched_episodes(
    session: Session,
    params: UnmatchedReadOptions,
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
    base = _unmatched_base(
        non_canonical_shows_only=params.non_canonical_shows_only,
    )
    filtered = _apply_filter_options(
        base,
        params.filter_options,
        _UNMATCHED_COLUMNS,
    )
    total_count = session.exec(
        select(func.count()).select_from(base.subquery()),
    ).one()
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            _expanded_sort_options(params.sort_options),
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
    source_numbers = absolute_numbers_of(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )
    used = _tmdb_ids_used_by_shows(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )
    description_matchers = _text_matchers(candidates, titles=False)
    title_matchers = _text_matchers(candidates, titles=True)

    return [
        UnmatchedEpisodeOutput(
            **_record_fields(episode, season, show),
            absolute_number=source_numbers.get(episode.id),
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
            season_episode_match=_marked_used(
                _season_and_episode_match(
                    episode,
                    season,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                ),
                episode.id,
                used.get(show.id, {}),
            ),
            absolute_number_match=_marked_used(
                _absolute_number_match(
                    episode,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                    source_numbers.get(episode.id),
                ),
                episode.id,
                used.get(show.id, {}),
            ),
            episode_number_absolute_match=_marked_used(
                _episode_number_absolute_match(
                    episode,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                ),
                episode.id,
                used.get(show.id, {}),
            ),
            description_embedding_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(show.id, {}))
                    for match in _text_matches(
                        episode,
                        description_matchers.get(show.id),
                        candidate_numbers.get(show.id, {}),
                        titles=False,
                        blended=False,
                    )
                )
                if choice is not None
            ],
            description_blended_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(show.id, {}))
                    for match in _text_matches(
                        episode,
                        description_matchers.get(show.id),
                        candidate_numbers.get(show.id, {}),
                        titles=False,
                        blended=True,
                    )
                )
                if choice is not None
            ],
            title_embedding_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(show.id, {}))
                    for match in _text_matches(
                        episode,
                        title_matchers.get(show.id),
                        candidate_numbers.get(show.id, {}),
                        titles=True,
                        blended=False,
                    )
                )
                if choice is not None
            ],
            title_blended_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(show.id, {}))
                    for match in _text_matches(
                        episode,
                        title_matchers.get(show.id),
                        candidate_numbers.get(show.id, {}),
                        titles=True,
                        blended=True,
                    )
                )
                if choice is not None
            ],
        )
        for episode, season, show, _source in rows
    ]


# TODO: Validate
def _marked_used(
    choice: TmdbEpisodeChoice | None,
    episode_id: uuid.UUID,
    used: dict[int, list[EpisodeRecord]],
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
        for entry in used.get(choice.episode.tmdb_id or 0, [])
        if entry.episode.id != episode_id
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
            col(Episode.canonical_episode_validated_at).is_(None),
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
    source_numbers = absolute_numbers_of(
        session,
        {show.id for _episode, _season, show, _source in rows},
    )

    outputs: list[UnlockedEpisodeOutput] = []
    for episode, season, show, _source in rows:
        best_match = _best_match(
            episode,
            season,
            candidates.get(show.id, []),
            candidate_numbers.get(show.id, {}),
        )
        outputs.append(
            UnlockedEpisodeOutput(
                **_record_fields(episode, season, show),
                absolute_number=source_numbers.get(episode.id),
                best_match=best_match,
                season_episode_match=_season_and_episode_match(
                    episode,
                    season,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                ),
                absolute_number_match=_absolute_number_match(
                    episode,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                    source_numbers.get(episode.id),
                ),
                episode_number_absolute_match=_episode_number_absolute_match(
                    episode,
                    candidates.get(show.id, []),
                    candidate_numbers.get(show.id, {}),
                ),
                name_matches=bool(
                    best_match
                    and plaintext(episode.name)
                    and plaintext(episode.name) == plaintext(best_match.episode.name),
                ),
            ),
        )
    return outputs


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


# TODO: Validate
def _duplicated_link_pairs(
    session: Session,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    uses = func.count(col(EpisodeCanonicalEpisode.episode_id).distinct())
    unsettled = func.bool_or(col(Episode.canonical_episode_validated_at).is_(None))
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
) -> dict[tuple[uuid.UUID, uuid.UUID], list[EpisodeRecord]]:
    canonical_episode_ids = {canonical_id for canonical_id, _source_id in pairs}
    statement = (
        select(  # type: ignore[call-overload]
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
            Episode,
            Season,
            Show,
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
        list[EpisodeRecord],
    ] = defaultdict(list)
    for canonical_id, source_id, episode, season, show in session.exec(statement).all():
        if (canonical_id, source_id) not in wanted:
            continue
        linking[canonical_id, source_id].append(
            EpisodeRecord(**_record_fields(episode, season, show)),
        )
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
        episode, season, show, _canonical_source = found
        outputs.append(
            DuplicatedCanonicalEpisodeOutput(
                id=f"{episode.id}:{source.id}",
                canonical=EpisodeRecord(**_record_fields(episode, season, show)),
                source=SourceListPublic.model_validate(source),
                linked_episodes=linking.get((canonical_id, source_id), []),
            ),
        )
    return sorted(
        outputs,
        key=lambda output: (
            output.source.name or "",
            output.canonical.show.name or "",
            output.canonical.season.season_number or 0,
            output.canonical.episode.episode_number or 0,
        ),
    )


# TODO: Validate
def _select_with_canonical_season_and_show() -> SelectOfScalar[Episode]:
    """Select episodes with the season and title above each one already loaded."""
    return (
        select(Episode)
        .join(
            Season,
            onclause=col(Episode.season_id) == Season.id,
        )
        .join(
            Show,
            onclause=col(Season.show_id) == Show.id,
        )
        .where(is_canonical(Episode), is_canonical(Show))
        .options(
            contains_eager(Episode.season).contains_eager(  # type: ignore[arg-type]
                Season.show,  # type: ignore[arg-type]
            ),
        )
    )


# TODO: Validate
def _information_side(  # noqa: PLR0913 - one side of the comparison, field by field.
    label: str,
    episode: Episode,
    season: Season,
    show: Show,
    url: str | None,
    absolute_number: int | None,
) -> EpisodeInformationSide:
    return EpisodeInformationSide(
        label=label,
        url=url,
        absolute_number=absolute_number,
        **_record_fields(episode, season, show),
    )


# TODO: Validate
def episode_information(
    session: Session,
    episode: Episode,
    user: User | None,
) -> EpisodeInformationOutput:
    """Return what the website and TMDB each say about an `Episode`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    season = episode.season
    show = season.show
    source = show.source

    # The episode itself, beside the website's account of it. Named for TMDB because
    # that is where a canonical row's values come from when TMDB has a record; media it
    # has never heard of is described by its one non-canonical row, so the two sides
    # read alike and the comparison is empty rather than misleading.
    counterpart = canonical_episode_of(session, episode.sole_canonical_episode_id)
    # Each side counts through its own title, so both titles are counted in one
    # go rather than a query apiece.
    numbers = absolute_numbers_of(
        session,
        {show.id} if counterpart is None else {show.id, counterpart[2].id},
    )
    tmdb: EpisodeInformationSide | None = None
    if counterpart:
        canonical_episode, canonical_season, canonical_show = counterpart
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            canonical_episode,
            canonical_season,
            canonical_show,
            tmdb_episode_url(
                canonical_show.key,
                canonical_season.season_number,
                canonical_episode.episode_number,
            ),
            numbers.get(canonical_episode.id),
        )

    canonical_episode_id = single_canonical_episode_id(episode)
    stored_url = (
        user_episode_url(session, user, canonical_episode_id)
        if canonical_episode_id
        else None
    )

    return EpisodeInformationOutput(
        episode_id=episode.id,
        user_url=stored_url.url if stored_url else None,
        canonical_episode_validated_at=episode.canonical_episode_validated_at,
        canonical_episode_note=episode.canonical_episode_note,
        issue_reports=list_episode_issue_reports(session, episode.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            episode,
            season,
            show,
            episode.url,
            numbers.get(episode.id),
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def non_canonical_episodes(episode: Episode) -> list[EpisodeListOutput]:
    """Get every website's row standing for an `Episode`.

    The other end of the link the non-canonical rows are settled by, which only a
    canonical episode ever has any of. Read by anybody, signed in or not: which
    websites carry an episode is as much a part of the episode as its name.
    """
    return [
        EpisodeListOutput.model_validate(link.episode)
        for link in episode.non_canonical_episodes
    ]


# TODO: Validate
def set_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
    url: str,
) -> UserEpisodeUrlOutput:
    """Point a `User`'s own copy of an `Episode` at a URL of their choosing."""
    canonical_episode_id = canonical_episode_for_url(episode)
    record = set_user_episode_url(session, current_user, canonical_episode_id, url)
    return UserEpisodeUrlOutput(
        canonical_episode_id=canonical_episode_id,
        url=record.url,
    )


# TODO: Validate
def clear_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
) -> UserEpisodeUrlOutput:
    """Drop the URL a `User` gave for an `Episode`."""
    canonical_episode_id = canonical_episode_for_url(episode)
    clear_user_episode_url(session, current_user, canonical_episode_id)
    return UserEpisodeUrlOutput(canonical_episode_id=canonical_episode_id, url=None)


# TODO: Validate
def canonical_episode_record(
    session: Session,
    canonical_episode: Episode,
) -> CanonicalEpisodeRecord:
    """Read an `Episode` with the season and title above it."""
    numbers = absolute_numbers_of(session, {canonical_episode.season.show_id})
    return CanonicalEpisodeRecord(
        absolute_number=numbers.get(canonical_episode.id),
        **episode_record(canonical_episode).model_dump(),
    )
