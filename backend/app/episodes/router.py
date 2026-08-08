# TODO: Validate
"""Episodes router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.episodes.dependencies import (
    EditableEpisode,
    ExistingEpisode,
    ReadableEpisode,
)
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeInformationOutput,
    EpisodeInformationSide,
    EpisodeListOutput,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeTmdbLinkInput,
    EpisodeUpdate,
    TmdbEpisodeChoice,
    UnlockedEpisodeOutput,
    UnmatchedEpisodeOutput,
)
from app.episodes.tmdb_matches import (
    confirm_no_tmdb_match,
    link_episode,
    list_tmdb_episode_choices,
    list_unlocked_episodes,
    list_unmatched_episodes,
)
from app.issue_reports.service import list_episode_issue_reports
from app.media.schemas import MediaReadOptions
from app.media.service import delete_record, media_scoped_list_response
from app.media.tmdb_fallback import (
    TMDB_PLUGIN_KEY,
    fill_episodes,
    tmdb_episode_counterpart,
    tmdb_episode_url,
)
from app.media.tmdb_identifier_links import check_episode_identifier
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.service import list_response
from app.shows.dependencies import ReadableShow
from app.shows.models import Show
from app.sources.dependencies import ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_episodes_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["episodes"])
source_episodes_router = APIRouter(prefix="/sources/{source_id}", tags=["episodes"])
show_episodes_router = APIRouter(prefix="/shows/{show_id}", tags=["episodes"])
season_episodes_router = APIRouter(prefix="/seasons/{season_id}", tags=["episodes"])
episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])

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


def _episode_output(session: SessionDep, episode: Episode) -> EpisodeOutput:
    """Return an `Episode` as TMDB has it, falling back on what its website said."""
    return fill_episodes(session, [EpisodeOutput.model_validate(episode)])[0]


@season_episodes_router.post("/episodes")
def create_episode(
    session: SessionDep,
    season: EditableSeason,
    episode_input: EpisodeCreate,
) -> EpisodeOutput:
    """Create an `Episode` if the `Season` is editable by the `User`.

    An `episode_identifier` naming a TMDB episode is checked before it is stored,
    and the title holding it is imported for the link to read.
    """
    check_episode_identifier(
        session,
        episode_input.episode_identifier,
        season.show.show_identifier,
    )
    return _episode_output(session, episode_input.create(session, Episode, season))


@episodes_router.get("")
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


@episodes_router.get(
    "/tmdb-matches",
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_get_unmatched_episodes(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnmatchedEpisodeOutput]:
    """Get the `Episode`s no TMDB record was found for, and the closest match to each."""
    return list_unmatched_episodes(session, limit)


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
    "/{episode_id}/tmdb-choices",  # noqa: FAST003 - Used by ExistingEpisode.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_get_tmdb_episode_choices(
    session: SessionDep,
    episode: ExistingEpisode,
) -> list[TmdbEpisodeChoice]:
    """Get every TMDB episode an `Episode` could be linked to, in the title's order."""
    return list_tmdb_episode_choices(session, episode)


@episodes_router.put(
    "/{episode_id}/tmdb-link",  # noqa: FAST003 - Used by ExistingEpisode.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_link_episode_to_tmdb(
    session: SessionDep,
    episode: ExistingEpisode,
    link_input: EpisodeTmdbLinkInput,
) -> EpisodeOutput:
    """Point an `Episode` at the TMDB episode an admin chose for it."""
    linked = link_episode(
        session,
        episode,
        link_input.tmdb_episode_id,
        selected=link_input.selected,
    )
    return _episode_output(session, linked)


@episodes_router.put(
    "/{episode_id}/tmdb-no-match",  # noqa: FAST003 - Used by ExistingEpisode.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_mark_episode_no_tmdb_match(
    session: SessionDep,
    episode: ExistingEpisode,
) -> EpisodeOutput:
    """Hold an `Episode` at its own identifier, TMDB having nothing to link it to."""
    return _episode_output(session, confirm_no_tmdb_match(session, episode))


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
        release_date=episode.release_date,
        air_date=episode.air_date,
        episode_number=episode.episode_number,
        sort_order=episode.sort_order,
        season_number=season.season_number,
        season_name=season.name,
        show_name=show.name,
        url=url,
        key=episode.key,
        episode_identifier=episode.episode_identifier,
        episode_identifier_locked=episode.episode_identifier_locked,
        episode_identifier_note=episode.episode_identifier_note,
        data_timestamp=episode.data_timestamp,
        update_at=episode.update_at,
        modified_at=episode.modified_at,
    )


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

    counterpart = tmdb_episode_counterpart(session, episode.episode_identifier)
    tmdb: EpisodeInformationSide | None = None
    if counterpart:
        tmdb_episode, tmdb_season, tmdb_show = counterpart
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            tmdb_episode,
            tmdb_season,
            tmdb_show,
            tmdb_episode_url(
                tmdb_show.key,
                tmdb_season.season_number,
                tmdb_episode.episode_number,
            ),
        )

    return EpisodeInformationOutput(
        episode_id=episode.id,
        episode_identifier=episode.episode_identifier,
        episode_identifier_locked=episode.episode_identifier_locked,
        episode_identifier_note=episode.episode_identifier_note,
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


@episodes_router.patch("/{episode_id}")  # noqa: FAST003 - Used by EditableEpisode.
def update_episode(
    session: SessionDep,
    episode: EditableEpisode,
    episode_input: EpisodeUpdate,
) -> EpisodeOutput:
    """Update and return an `Episode` if it's editable by the `User`.

    A new `episode_identifier` naming a TMDB episode is checked before it is
    stored, so an episode the title does not have is refused rather than kept as
    a link to nothing, and the title is imported for the link to read.
    """
    if (
        episode_input.episode_identifier is not None
        and episode_input.episode_identifier != episode.episode_identifier
    ):
        check_episode_identifier(
            session,
            episode_input.episode_identifier,
            episode.season.show.show_identifier,
        )
    return _episode_output(session, episode_input.update(session, episode))


@episodes_router.delete("/{episode_id}")  # noqa: FAST003 - Used by EditableEpisode.
def delete_episode(session: SessionDep, episode: EditableEpisode) -> Message:
    """Delete an `Episode` if it's editable by the `User`."""
    return delete_record(session, episode)


router = APIRouter()
router.include_router(episodes_router)
router.include_router(season_episodes_router)
router.include_router(show_episodes_router)
router.include_router(source_episodes_router)
router.include_router(plugin_episodes_router)
