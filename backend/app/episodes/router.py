# TODO: Validate
"""Episodes router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import contains_eager
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.canonical_media.filters import is_canonical
from app.canonical_media.metadata import (
    canonical_episode_of,
    fill_episodes,
    tmdb_episode_url,
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
    EditableEpisode,
    ExistingEpisode,
    ReadableEpisode,
)
from app.episodes.models import Episode
from app.episodes.schemas import (
    CanonicalEpisodeListOutput,
    CanonicalEpisodeOutput,
    CanonicalEpisodesPublic,
    DuplicatedCanonicalEpisodeOutput,
    EpisodeCreate,
    EpisodeInformationOutput,
    EpisodeInformationSide,
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
    get_duplicated_canonical_episodes,
    list_tmdb_episode_choices,
    list_unlocked_episodes,
    list_unmatched_episodes,
)
from app.issue_reports.service import list_episode_issue_reports
from app.media.schemas import MediaReadOptions
from app.media.service import delete_record, media_scoped_list_response
from app.plugins.dependencies import ReadablePlugin
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.service import list_response
from app.shows.dependencies import AdminCanonicalShow, ReadableShow
from app.shows.models import Show
from app.sources.dependencies import ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_episodes_router = APIRouter(
    prefix="/plugins/{plugin_id}",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)
source_episodes_router = APIRouter(
    prefix="/sources/{source_id}",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)
show_episodes_router = APIRouter(
    prefix="/shows/{show_id}",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)
season_episodes_router = APIRouter(
    prefix="/seasons/{season_id}",
    tags=["episodes"],
    dependencies=[Depends(get_current_active_superuser)],
)
episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])
canonical_show_episodes_router = APIRouter(
    prefix="/shows/canonical/{canonical_show_id}",
    tags=["canonical-episodes"],
)
canonical_episodes_router = APIRouter(
    prefix="/episodes/canonical",
    tags=["canonical-episodes"],
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
    "username": User.username,
    "season_name": Season.name,
    "show_id": Season.show_id,
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
def _episode_output(session: SessionDep, episode: Episode) -> EpisodeOutput:
    """Return an `Episode` as TMDB has it, falling back on what its website said."""
    return fill_episodes(session, [EpisodeOutput.model_validate(episode)])[0]


# TODO: Validate
@season_episodes_router.post("/episodes")
def create_episode(
    session: SessionDep,
    season: EditableSeason,
    episode_input: EpisodeCreate,
) -> EpisodeOutput:
    """Create an `Episode` if the `Season` is editable by the `User`."""
    return _episode_output(session, episode_input.create(session, Episode, season))


# TODO: Validate
@episodes_router.get("", dependencies=[Depends(get_current_active_superuser)])
def get_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> EpisodesPublic:
    """Get `Episode`s."""
    episodes = media_scoped_list_response(
        session=session,
        base=Episode.select_with_user_eager(),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )
    fill_episodes(session, episodes.data)
    return episodes


# TODO: Validate
@season_episodes_router.get("/episodes")
def get_season_episodes(
    session: SessionDep,
    season: ReadableSeason,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Season` if it is readable by the `User`."""
    episodes = list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Episode.season_id == season.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )
    fill_episodes(session, episodes.data)
    return episodes


# TODO: Validate
@plugin_episodes_router.get("/episodes")
def get_plugin_episodes(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Plugin` if it is readable by the `User`."""
    episodes = list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )
    fill_episodes(session, episodes.data)
    return episodes


# TODO: Validate
@source_episodes_router.get("/episodes")
def get_source_episodes(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Source` if it is readable by the `User`."""
    episodes = list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Show.source_id == source.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )
    fill_episodes(session, episodes.data)
    return episodes


# TODO: Validate
@show_episodes_router.get("/episodes")
def get_show_episodes(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Show` if it is readable by the `User`."""
    episodes = list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Season.show_id == show.id),
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_get_unlocked_episodes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnlockedEpisodeOutput]:
    """Get every `Episode` whose TMDB link no `User` has settled."""
    return list_unlocked_episodes(session, limit)


@episodes_router.get(
    "/duplicated-canonical-episodes",
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
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
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_verify_canonical_link(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Settle the canonical links an `Episode` already carries, and lock them."""
    return _episode_output(session, verify_canonical_link(session, episode))


# TODO: Validate
def _information_side(
    label: str,
    episode: Episode,
    season: Season,
    show: Show,
    url: str | None,
) -> EpisodeInformationSide:
    return EpisodeInformationSide(
        label=label,
        name=episode.name,
        description=episode.description,
        image_url=episode.image_url,
        duration=episode.duration,
        air_date=episode.air_date,
        episode_number=episode.episode_number,
        sort_order=episode.sort_order,
        season_number=season.season_number,
        season_name=season.name,
        show_id=show.id,
        show_name=show.name,
        url=url,
        key=episode.key,
        canonical_episode_validated_at=episode.canonical_episode_validated_at,
        canonical_episode_note=episode.canonical_episode_note,
        data_timestamp=episode.data_timestamp,
        update_at=episode.update_at,
        modified_at=episode.modified_at,
    )


# TODO: Validate
@episodes_router.get("/{episode_id}/information")  # noqa: FAST003 - Used by ReadableEpisode.
def get_episode_information(
    session: SessionDep,
    episode: ReadableEpisode,
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
        )

    return EpisodeInformationOutput(
        episode_id=episode.id,
        canonical_episode_validated_at=episode.canonical_episode_validated_at,
        canonical_episode_note=episode.canonical_episode_note,
        issue_reports=list_episode_issue_reports(session, episode.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            episode,
            season,
            show,
            episode.url,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
@episodes_router.get(
    "/{episode_id}",  # noqa: FAST003 - Used by EditableEpisode.
    dependencies=[Depends(get_current_active_superuser)],
)
def get_episode(session: SessionDep, episode: EditableEpisode) -> EpisodeOutput:
    return _episode_output(session, episode)


# TODO: Validate
@episodes_router.patch(
    "/{episode_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def update_episode(
    session: SessionDep,
    episode: EditableEpisode,
    episode_input: EpisodeUpdate,
) -> EpisodeOutput:
    """Update and return an `Episode` if it's editable by the `User`.

    Which episode this is linked to is settled by the TMDB matching screens
    rather than written here, so there is nothing to check.
    """
    return _episode_output(session, episode_input.update(session, episode))


# TODO: Validate
@episodes_router.delete(
    "/{episode_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_episode(session: SessionDep, episode: EditableEpisode) -> Message:
    """Delete an `Episode` if it's editable by the `User`."""
    return delete_record(session, episode)


# The admin-only mirror of the episode endpoints.
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


# TODO: Validate
@canonical_show_episodes_router.get("/episodes")
def get_canonical_show_episodes(
    session: SessionDep,
    canonical_show: AdminCanonicalShow,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalEpisodesPublic:
    """Get every `Episode` under one `Show`, across its seasons."""
    return canonical_list_response(
        session=session,
        base=_select_with_canonical_season_and_show().where(
            Season.show_id == canonical_show.id,
        ),
        response_model=CanonicalEpisodesPublic,
        schema=CanonicalEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_EPISODE_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_episodes_router.get("/{canonical_episode_id}")  # noqa: FAST003 - Used by AdminCanonicalEpisode.
def get_canonical_episode_by_id(
    canonical_episode: AdminCanonicalEpisode,
) -> CanonicalEpisodeOutput:
    """Get a `Episode`."""
    return CanonicalEpisodeOutput.model_validate(canonical_episode)


router = APIRouter()
# Registered ahead of `episodes_router` so "/episodes/canonical" is read as the
# canonical listing rather than as an `Episode` id that happens to be misspelt.
router.include_router(canonical_episodes_router)
router.include_router(canonical_show_episodes_router)
router.include_router(episodes_router)
router.include_router(season_episodes_router)
router.include_router(show_episodes_router)
router.include_router(source_episodes_router)
router.include_router(plugin_episodes_router)
