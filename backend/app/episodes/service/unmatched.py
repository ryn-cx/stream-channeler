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
from typing import Any

from sqlalchemy.orm import aliased, contains_eager
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import is_canonical, is_non_canonical
from app.channels.models import Channel, ChannelTitle
from app.episodes.models import (
    Episode,
    EpisodeCanonicalEpisode,
)
from app.episodes.schemas import (
    EpisodeRecord,
    TmdbEpisodeChoice,
    UnmatchedEpisodeOutput,
    UnmatchedEpisodesPublic,
    UnmatchedReadOptions,
)
from app.episodes.service.numbering import (
    _absolute_number_match,
    _best_match,
    _candidates_for_titles,
    _episode_number_absolute_match,
    _season_and_episode_match,
    _text_matchers,
    _text_matches,
    absolute_numbers_of,
)
from app.episodes.service.records import _record_fields
from app.episodes.service.tmdb_choices import _tmdb_ids_used_by_titles
from app.plugins.models import Plugin
from app.schemas import SortOption
from app.seasons.models import Season
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.sources.models import Source
from app.titles.models import Title, TitleCanonicalTitle
from app.users.models import User
from app.users.plugin_user import is_plugin_user


# TODO: Validate
def _in_a_channel() -> ColumnElement[bool]:
    channel_owner = aliased(User)
    return (
        select(ChannelTitle.channel_id)
        .select_from(ChannelTitle)
        .join(Channel, onclause=col(ChannelTitle.channel_id) == Channel.id)
        .join(channel_owner, onclause=col(Channel.user_id) == channel_owner.id)
        .where(
            col(ChannelTitle.is_blacklist_only).is_(False),
            ~is_plugin_user(channel_owner.email),
            or_(
                col(ChannelTitle.canonical_title_id).in_(
                    select(TitleCanonicalTitle.canonical_title_id)
                    .where(col(TitleCanonicalTitle.title_id) == col(Title.id))
                    .correlate(Title),
                ),
                and_(
                    is_canonical(Title),
                    col(ChannelTitle.canonical_title_id) == col(Title.id),
                ),
            ),
        )
        .correlate(Title)
        .exists()
    )


# TODO: Validate
# Which joined column each sortable name is, since a name a non-canonical row is not
# sorted by on its own row - the title it is under, the source that carries it - has no
# column of `Episode` to be read off.
_UNMATCHED_COLUMNS: dict[str, Any] = {
    # The combined column reads as the title it is under first, so that is what
    # sorting or filtering it is asking about.
    "summary": Title.name,
    "title_name": Title.name,
    "title_year": Title.year,
    "source_key": Source.key,
    "plugin_name": Plugin.key,
    "season_name": Season.name,
    "season_number": Season.season_number,
    "episode_name": Episode.name,
    "episode_number": Episode.episode_number,
    # A note is written against the link rather than against the episode, so the
    # one column a row can be sorted or filtered by is read off the links the
    # row carries.
    "identifier_note": (
        select(func.min(col(EpisodeCanonicalEpisode.note)))
        .where(col(EpisodeCanonicalEpisode.episode_id) == col(Episode.id))
        .correlate(Episode)
        .scalar_subquery()
    ),
}


# TODO: Validate
def _unmatched_base(
    *,
    non_canonical_titles_only: bool = False,
) -> SelectOfScalar[Episode]:
    """The rows the page is drawn from, before anything is sorted, filtered or
    counted. `contains_eager` carries the season, title and source back with each
    episode, since every one of them is read for every row and reaching them
    through the relationships would be three queries a row.
    """
    return (
        select(Episode)
        .select_from(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .join(Plugin, onclause=col(Source.plugin_id) == Plugin.id)
        .options(
            contains_eager(Episode.season)  # type: ignore[arg-type]
            .contains_eager(Season.title)  # type: ignore[arg-type]
            .contains_eager(Title.source)  # type: ignore[arg-type]
            .contains_eager(Source.plugin),  # type: ignore[arg-type]
        )
        .where(
            col(Source.link_to_tmdb).is_(True),
            is_canonical(Episode),
            # An episode settled as one TMDB has no record of points at nothing
            # and is locked there, which reads as canonical the same way one
            # nothing has worked out yet does. The lock is what tells them
            # apart, and a settled episode is waiting on nobody.
            col(Episode.canonical_episode_validated_at).is_(None),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
            _in_a_channel(),
            *([is_non_canonical(Title)] if non_canonical_titles_only else []),
        )
    )


# TODO: Validate
def _expanded_sort_options(sort_options: list[SortOption]) -> list[SortOption]:
    expanded: list[SortOption] = []
    for option in sort_options:
        expanded.append(option)
        if option.column == "summary":
            expanded += [
                SortOption(id="source_key", desc=option.desc),
                SortOption(id="season_number", desc=option.desc),
                SortOption(id="episode_number", desc=option.desc),
            ]
    return expanded


# TODO: Validate
def list_unmatched_episodes(
    session: Session,
    params: UnmatchedReadOptions,
) -> UnmatchedEpisodesPublic:
    """Sorted, filtered and paged by the database rather than in the browser. There
    are far more of these than a page titles, so ordering a page of them would
    order only the ones already fetched: sorting by name would answer with the
    first names of whichever rows came back, not the first names there are.

    Always server-side, unlike the hybrid tables. The closest TMDB episode is
    worked out by comparing names in Python, which is worth doing for the twenty
    rows being shown and not for every row there is.
    """
    base = _unmatched_base(
        non_canonical_titles_only=params.non_canonical_titles_only,
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
            [Episode.created_at],
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
        (episode, episode.season, episode.season.title, episode.season.title.source)
        for episode in episodes
    ]
    candidates, candidate_numbers = _candidates_for_titles(
        session,
        {title for _episode, _season, title, _source in rows},
    )
    source_numbers = absolute_numbers_of(
        session,
        {title.id for _episode, _season, title, _source in rows},
    )
    used = _tmdb_ids_used_by_titles(
        session,
        {title.id for _episode, _season, title, _source in rows},
    )
    description_matchers = _text_matchers(candidates, titles=False)
    title_matchers = _text_matchers(candidates, titles=True)

    return [
        UnmatchedEpisodeOutput(
            **_record_fields(episode, season, title),
            absolute_number=source_numbers.get(episode.id),
            best_match=_marked_used(
                _best_match(
                    episode,
                    season,
                    candidates.get(title.id, []),
                    candidate_numbers.get(title.id, {}),
                ),
                episode.id,
                used.get(title.id, {}),
            ),
            season_episode_match=_marked_used(
                _season_and_episode_match(
                    episode,
                    season,
                    candidates.get(title.id, []),
                    candidate_numbers.get(title.id, {}),
                ),
                episode.id,
                used.get(title.id, {}),
            ),
            absolute_number_match=_marked_used(
                _absolute_number_match(
                    episode,
                    candidates.get(title.id, []),
                    candidate_numbers.get(title.id, {}),
                    source_numbers.get(episode.id),
                ),
                episode.id,
                used.get(title.id, {}),
            ),
            episode_number_absolute_match=_marked_used(
                _episode_number_absolute_match(
                    episode,
                    candidates.get(title.id, []),
                    candidate_numbers.get(title.id, {}),
                ),
                episode.id,
                used.get(title.id, {}),
            ),
            description_embedding_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(title.id, {}))
                    for match in _text_matches(
                        episode,
                        description_matchers.get(title.id),
                        candidate_numbers.get(title.id, {}),
                        titles=False,
                        blended=False,
                    )
                )
                if choice is not None
            ],
            description_blended_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(title.id, {}))
                    for match in _text_matches(
                        episode,
                        description_matchers.get(title.id),
                        candidate_numbers.get(title.id, {}),
                        titles=False,
                        blended=True,
                    )
                )
                if choice is not None
            ],
            title_embedding_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(title.id, {}))
                    for match in _text_matches(
                        episode,
                        title_matchers.get(title.id),
                        candidate_numbers.get(title.id, {}),
                        titles=True,
                        blended=False,
                    )
                )
                if choice is not None
            ],
            title_blended_matches=[
                choice
                for choice in (
                    _marked_used(match, episode.id, used.get(title.id, {}))
                    for match in _text_matches(
                        episode,
                        title_matchers.get(title.id),
                        candidate_numbers.get(title.id, {}),
                        titles=True,
                        blended=True,
                    )
                )
                if choice is not None
            ],
        )
        for episode, season, title, _source in rows
    ]


# TODO: Validate
def _marked_used(
    choice: TmdbEpisodeChoice | None,
    episode_id: uuid.UUID,
    used: dict[int, list[EpisodeRecord]],
) -> TmdbEpisodeChoice | None:
    """Say which of the title's other episodes already point at `choice`.

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
