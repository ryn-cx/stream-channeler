# TODO: Validate


import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.episodes.dependencies import (
    AdminTmdbEpisode,
    ExistingEpisode,
)
from app.episodes.models import Episode
from app.episodes.schemas import (
    DuplicatedTmdbEpisodeOutput,
    EpisodeDatabaseOutput,
    EpisodeListOutput,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeTmdbLinkInput,
    EpisodeTmdbUrlInput,
    EpisodeUpdate,
    TmdbEpisodeChoice,
    TmdbEpisodeListOutput,
    TmdbEpisodesPublic,
    UnlockedEpisodeOutput,
    UnmatchedEpisodesPublic,
    UnmatchedReadOptions,
)
from app.episodes.service.database_rows import episode_database_rows
from app.episodes.service.duplicates import get_duplicated_tmdb_episodes
from app.episodes.service.information import _select_with_tmdb_season_and_title
from app.episodes.service.tmdb_choices import list_tmdb_episode_choices
from app.episodes.service.unlocked import list_unlocked_episodes
from app.episodes.service.unmatched import list_unmatched_episodes
from app.episodes.tmdb_links import (
    link_episode,
    link_episode_using_tmdb_url,
    link_episodes,
    mark_episode_absent_from_tmdb,
    mark_episodes_absent_from_tmdb,
    quick_unlink_episode,
    unlink_episode,
    verify_tmdb_link,
)
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.service.responses import list_response
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.read import tmdb_list_response

"""Episodes router."""


tmdb_episodes_router = APIRouter(
    prefix="/episodes/tmdb",
    tags=["tmdb-episodes"],
)


episodes_router = APIRouter(
    prefix="/episodes",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)


TMDB_EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "tmdb_season_id": Episode.season_id,
    "tmdb_season_name": Season.name,
    "tmdb_title_id": Season.title_id,
    "tmdb_title_name": Title.name,
    "tmdb_title_key": Title.key,
}


EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "season_name": Season.name,
    "title_id": Season.title_id,
    "title_name": Title.name,
    "source_id": Title.source_id,
    "source_key": Source.key,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.key,
}


# TODO: Validate
@episodes_router.get("")
def get_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get `Episode`s."""
    return list_response(
        session=session,
        base=Episode.select_with_plugin_eager(),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


# TODO: Validate
@episodes_router.get("/tmdb-matches")
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
    "/duplicated-tmdb-episodes",
)
def admin_get_duplicated_tmdb_episodes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[DuplicatedTmdbEpisodeOutput]:
    """Get every canonical `Episode` that has multiple non-canonical `Episode`s linked to
    it from a single source."""
    return get_duplicated_tmdb_episodes(session, limit)


# TODO: Validate
@episodes_router.put("/tmdb-links")
def admin_link_episodes_to_tmdb(
    session: SessionDep,
    links: list[EpisodeTmdbLinkInput],
) -> list[EpisodeOutput]:
    return [
        EpisodeOutput.model_validate(episode)
        for episode in link_episodes(session, links)
    ]


# TODO: Validate
@episodes_router.put("/tmdb-absent")
def admin_mark_episodes_absent_from_tmdb(
    session: SessionDep,
    episode_ids: list[uuid.UUID],
) -> list[EpisodeOutput]:
    return [
        EpisodeOutput.model_validate(episode)
        for episode in mark_episodes_absent_from_tmdb(session, episode_ids)
    ]


# TODO: Validate
@episodes_router.get(
    "/{episode_id}/database",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_get_episode_database_rows(
    episode: ExistingEpisode,
) -> EpisodeDatabaseOutput:
    return episode_database_rows(episode)


# TODO: Validate
@episodes_router.get(
    "/{episode_id}/tmdb-choices",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_get_tmdb_episode_choices(
    session: SessionDep,
    episode: ExistingEpisode,
    name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[TmdbEpisodeChoice]:
    """Get every TMDB episode an `Episode` could be linked to, in the title's order."""
    return list_tmdb_episode_choices(session, episode, name, limit)


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
    pointed at, and so that a title the title was not a non-canonical row of is linked to
    it as well.
    """
    return EpisodeOutput.model_validate(
        link_episode_using_tmdb_url(session, episode, url_input.url),
    )


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb/{tmdb_episode_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_episode_to_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
    tmdb_episode: AdminTmdbEpisode,
) -> EpisodeOutput:
    """Add the episode an admin chose to what an `Episode` stands for.

    The episode chosen is one already stored, since the choices are read off the
    stored rows, so it is named by its own id and there is nothing to read in.

    Added to whatever the row already stands for rather than put in its place,
    since a website running two episodes together in one listing is a thing
    websites do. Taking one off is `admin_unlink_episode_from_tmdb_episode`.
    """
    return EpisodeOutput.model_validate(
        link_episode(session, episode, tmdb_episode),
    )


# TODO: Validate
@episodes_router.delete(
    "/{episode_id}/tmdb/{tmdb_episode_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_unlink_episode_from_tmdb_episode(
    session: SessionDep,
    episode: ExistingEpisode,
    tmdb_episode: AdminTmdbEpisode,
) -> EpisodeOutput:
    """Take one episode off what an `Episode` stands for."""
    return EpisodeOutput.model_validate(
        unlink_episode(session, episode, tmdb_episode),
    )


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-quick-unlink",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_quick_unlink_episode(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    return EpisodeOutput.model_validate(quick_unlink_episode(session, episode))


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-unlink",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_unlink_episode_from_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Take an `Episode` off the TMDB episode it was pointed at."""
    return EpisodeOutput.model_validate(unlink_episode(session, episode))


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/tmdb-absent",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_mark_episode_absent_from_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Settle an `Episode` as one TMDB has no record of, and lock it there."""
    return EpisodeOutput.model_validate(mark_episode_absent_from_tmdb(session, episode))


# TODO: Validate
@episodes_router.put(
    "/{episode_id}/verify-tmdb-link",  # noqa: FAST003 - Used by ExistingEpisode.
)
def admin_verify_tmdb_link(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Settle the canonical links an `Episode` already carries, and lock them."""
    return EpisodeOutput.model_validate(verify_tmdb_link(session, episode))


# TODO: Validate
@episodes_router.get(
    "/{episode_id}",  # noqa: FAST003 - Used by ExistingEpisode.
)
def get_episode(episode: ExistingEpisode) -> EpisodeOutput:
    return EpisodeOutput.model_validate(episode)


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
    return EpisodeOutput.model_validate(episode_input.update(session, episode))


# TODO: Validate
@tmdb_episodes_router.get("")
def get_tmdb_episodes(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> TmdbEpisodesPublic:
    """Get every `Episode`."""
    return tmdb_list_response(
        session=session,
        base=_select_with_tmdb_season_and_title(),
        response_model=TmdbEpisodesPublic,
        schema=TmdbEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=TMDB_EPISODE_EXTRA_COLUMNS,
    )


router = APIRouter()


router.include_router(tmdb_episodes_router)


router.include_router(episodes_router)
