# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.canonical_media.metadata import (
    canonical_episode_of,
    tmdb_episode_url,
)
from app.episodes.dependencies import (
    AdminCanonicalEpisode,
    ExistingEpisode,
)
from app.episodes.schemas import (
    CanonicalEpisodeRecord,
    EpisodeInformationOutput,
    EpisodeInformationSide,
    EpisodeListOutput,
    UserEpisodeUrlInput,
    UserEpisodeUrlOutput,
)
from app.episodes.service import (
    _information_side,
    absolute_numbers_of,
    episode_record,
)
from app.episodes.user_urls import (
    canonical_episode_for_url,
    clear_user_episode_url,
    set_user_episode_url,
    single_canonical_episode_id,
    user_episode_url,
)
from app.issue_reports.service import list_episode_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.users.dependencies import OptionalUser

"""Episodes router."""


canonical_episodes_router = APIRouter(
    prefix="/episodes/canonical",
    tags=["canonical-episodes"],
)


episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])


# TODO: Validate
@episodes_router.get("/{episode_id}/information")  # noqa: FAST003 - Used by ExistingEpisode.
def get_episode_information(
    session: SessionDep,
    episode: ExistingEpisode,
    user: OptionalUser,
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
@episodes_router.get(
    "/{episode_id}/non-canonical",  # noqa: FAST003 - Used by ExistingEpisode.
)
def get_non_canonical_episodes(episode: ExistingEpisode) -> list[EpisodeListOutput]:
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
@episodes_router.put("/{episode_id}/user-url")  # noqa: FAST003 - Used by ExistingEpisode.
def set_episode_user_url(
    session: SessionDep,
    episode: ExistingEpisode,
    current_user: CurrentUser,
    url_input: UserEpisodeUrlInput,
) -> UserEpisodeUrlOutput:
    canonical_episode_id = canonical_episode_for_url(episode)
    record = set_user_episode_url(
        session,
        current_user,
        canonical_episode_id,
        url_input.url,
    )
    return UserEpisodeUrlOutput(
        canonical_episode_id=canonical_episode_id,
        url=record.url,
    )


# TODO: Validate
@episodes_router.delete("/{episode_id}/user-url")  # noqa: FAST003 - Used by ExistingEpisode.
def delete_episode_user_url(
    session: SessionDep,
    episode: ExistingEpisode,
    current_user: CurrentUser,
) -> UserEpisodeUrlOutput:
    canonical_episode_id = canonical_episode_for_url(episode)
    clear_user_episode_url(session, current_user, canonical_episode_id)
    return UserEpisodeUrlOutput(
        canonical_episode_id=canonical_episode_id,
        url=None,
    )


# TODO: Validate
@canonical_episodes_router.get("/{canonical_episode_id}")  # noqa: FAST003 - Used by AdminCanonicalEpisode.
def get_canonical_episode_by_id(
    session: SessionDep,
    canonical_episode: AdminCanonicalEpisode,
) -> CanonicalEpisodeRecord:
    """Get a `Episode`, with the season and title above it."""
    show_id = canonical_episode.season.show_id
    numbers = absolute_numbers_of(session, {show_id})
    return CanonicalEpisodeRecord(
        absolute_number=numbers.get(canonical_episode.id),
        **episode_record(canonical_episode).model_dump(),
    )


router = APIRouter()


router.include_router(canonical_episodes_router)


router.include_router(episodes_router)
