# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

from sqlalchemy.orm import contains_eager
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import is_canonical
from app.canonical_media.metadata import canonical_episode_of, tmdb_episode_url
from app.episodes.models import (
    Episode,
)
from app.episodes.schemas import (
    CanonicalEpisodeRecord,
    EpisodeInformationOutput,
    EpisodeInformationSide,
    EpisodeListOutput,
)
from app.episodes.service.numbering import absolute_numbers_of
from app.episodes.service.records import _record_fields, episode_record
from app.episodes.user_urls import (
    single_canonical_episode_id,
    user_episode_url,
)
from app.issue_reports.service.listing import list_episode_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User


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
            source.name or source.plugin.key,
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
