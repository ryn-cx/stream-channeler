# TODO: Validate


from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.canonical_media.metadata import (
    fill_episodes,
)
from app.canonical_media.read import canonical_list_response
from app.episodes.canonical_links import (
    link_episode,
    link_episode_using_tmdb_url,
    mark_episode_absent_from_tmdb,
    unlink_episode,
    verify_canonical_link,
)
from app.episodes.dependencies import (
    AdminCanonicalEpisode,
    ExistingEpisode,
)
from app.episodes.models import Episode
from app.episodes.schemas import (
    CanonicalEpisodeListOutput,
    CanonicalEpisodesPublic,
    DuplicatedCanonicalEpisodeOutput,
    EpisodeCreate,
    EpisodeListOutput,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeTmdbUrlInput,
    EpisodeUpdate,
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodesPublic,
    UnmatchedReadOptions,
)
from app.episodes.service import (
    _episode_output,
    _select_with_canonical_season_and_show,
    get_duplicated_canonical_episodes,
    list_tmdb_episode_choices,
    list_unlocked_episodes,
    list_unmatched_episodes,
)
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import ExistingSeason
from app.seasons.models import Season
from app.service import list_response
from app.shows.models import Show
from app.sources.models import Source

"""Episodes router."""


canonical_episodes_router = APIRouter(
    prefix="/episodes/canonical",
    tags=["canonical-episodes"],
)


episodes_router = APIRouter(
    prefix="/episodes",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)


season_episodes_router = APIRouter(
    prefix="/seasons/{season_id}",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)


# Every column the canonical list is sorted and filtered by that an `Episode` does not
# answer to under the name it is served as. `canonical_season_id` is among them now that
# an episode hangs off its season by `season_id` like any non-canonical row: without it
# here the column is silently unsortable.
CANONICAL_EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "canonical_season_id": Episode.season_id,
    "canonical_season_name": Season.name,
    "canonical_show_id": Season.show_id,
    "canonical_show_name": Show.name,
    "canonical_show_key": Show.key,
}


EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "season_name": Season.name,
    "show_id": Season.show_id,
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
@season_episodes_router.post("/episodes")
def create_episode(
    session: SessionDep,
    season: ExistingSeason,
    episode_input: EpisodeCreate,
) -> EpisodeOutput:
    return _episode_output(session, episode_input.create(session, Episode, season))


# TODO: Validate
@episodes_router.get("")
def get_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get `Episode`s."""
    episodes = list_response(
        session=session,
        base=Episode.select_with_plugin_eager(),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )
    fill_episodes(session, episodes.data)
    return episodes


# TODO: Validate
@episodes_router.get(
    "/tmdb-matches",
)
def admin_get_unmatched_episodes(
    session: SessionDep,
    read_options: Annotated[UnmatchedReadOptions, Query()],
) -> UnmatchedEpisodesPublic:
    """Get a page of the canonical `Episode`s outside TMDB and YouTube."""
    return list_unmatched_episodes(session, read_options)


# TODO: Validate
@episodes_router.get(
    "/unlocked",
)
def admin_get_unlocked_episodes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnlockedEpisodeOutput]:
    """Get every `Episode` whose TMDB link no `User` has settled."""
    return list_unlocked_episodes(session, limit)


# TODO: Validate
@episodes_router.get(
    "/duplicated-canonical-episodes",
)
def admin_get_duplicated_canonical_episodes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[DuplicatedCanonicalEpisodeOutput]:
    """Get every canonical `Episode` that has multiple non-canonical `Episode`s linked to
    it from a single source."""
    return get_duplicated_canonical_episodes(session, limit)


# TODO: Validate
@episodes_router.get(
    "/{episode_id}/tmdb-choices",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_get_tmdb_episode_choices(
    session: SessionDep,
    episode: ExistingEpisode,
    tmdb_show_id: int | None = None,
    name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[TmdbEpisodeChoice]:
    """Get every TMDB episode an `Episode` could be linked to, in the title's order.

    `tmdb_show_id` reads the episodes of a series other than the one the show is
    linked to, which is what reaches an episode TMDB files under its own title.
    """
    return list_tmdb_episode_choices(session, episode, tmdb_show_id, name, limit)


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-url",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_link_episode_by_tmdb_url(
    session: SessionDep,
    episode: ExistingEpisode,
    url_input: EpisodeTmdbUrlInput,
) -> EpisodeOutput:
    """Point an `Episode` at the TMDB record a themoviedb.org address names.

    Read here rather than in the browser so that the title is imported on the way, which
    is what turns the numbering in an episode's address into the record the episode is
    pointed at, and so that a title the show was not a non-canonical row of is linked to
    it as well.
    """
    return _episode_output(
        session,
        link_episode_using_tmdb_url(session, episode, url_input.url),
    )


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/canonical/{canonical_episode_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_episode_to_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
    canonical_episode: AdminCanonicalEpisode,
) -> EpisodeOutput:
    """Add the episode an admin chose to what an `Episode` stands for.

    The episode chosen is one already stored, since the choices are read off the
    stored rows, so it is named by its own id and there is nothing to read in.

    Added to whatever the row already stands for rather than put in its place,
    since a website running two episodes together in one listing is a thing
    websites do. Taking one off is `admin_unlink_episode_from_canonical`.
    """
    return _episode_output(
        session,
        link_episode(session, episode, canonical_episode),
    )


# TODO: Validate
@episodes_router.delete(
    "/{episode_id}/canonical/{canonical_episode_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_unlink_episode_from_canonical(
    session: SessionDep,
    episode: ExistingEpisode,
    canonical_episode: AdminCanonicalEpisode,
) -> EpisodeOutput:
    """Take one episode off what an `Episode` stands for."""
    return _episode_output(
        session,
        unlink_episode(session, episode, canonical_episode),
    )


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-unlink",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_unlink_episode_from_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Take an `Episode` off the TMDB episode it was pointed at."""
    return _episode_output(session, unlink_episode(session, episode))


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-absent",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_mark_episode_absent_from_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Settle an `Episode` as one TMDB has no record of, and lock it there."""
    return _episode_output(
        session,
        mark_episode_absent_from_tmdb(session, episode),
    )


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/verify-canonical-link",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_verify_canonical_link(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Settle the canonical links an `Episode` already carries, and lock them."""
    return _episode_output(session, verify_canonical_link(session, episode))


# TODO: Validate
@episodes_router.get(
    "/{episode_id}",  # noqa: FAST003 - Used by ExistingEpisode.
)
def get_episode(session: SessionDep, episode: ExistingEpisode) -> EpisodeOutput:
    return _episode_output(session, episode)


# TODO: Validate
@episodes_router.patch(
    "/{episode_id}",
)
def update_episode(
    session: SessionDep,
    episode: ExistingEpisode,
    episode_input: EpisodeUpdate,
) -> EpisodeOutput:
    """Which episode this is linked to is settled by the TMDB matching screens
    rather than written here, so there is nothing to check.
    """
    return _episode_output(session, episode_input.update(session, episode))


# TODO: Validate
@episodes_router.delete(
    "/{episode_id}",
)
def delete_episode(session: SessionDep, episode: ExistingEpisode) -> Message:
    return delete_record(session, episode)


# TODO: Validate
@canonical_episodes_router.get("")
def get_canonical_episodes(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalEpisodesPublic:
    """Get every `Episode`."""
    return canonical_list_response(
        session=session,
        base=_select_with_canonical_season_and_show(),
        response_model=CanonicalEpisodesPublic,
        schema=CanonicalEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_EPISODE_EXTRA_COLUMNS,
    )


router = APIRouter()


router.include_router(canonical_episodes_router)


router.include_router(episodes_router)


router.include_router(season_episodes_router)


