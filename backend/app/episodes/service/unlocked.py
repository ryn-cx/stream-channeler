# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    tmdb_key_clause,
)
from app.episodes.models import (
    Episode,
)
from app.episodes.name_matching import (
    plaintext,
)
from app.episodes.schemas import (
    UnlockedEpisodeOutput,
)
from app.episodes.service.numbering import (
    _absolute_number_match,
    _best_match,
    _candidates_for_shows,
    _episode_number_absolute_match,
    _season_and_episode_match,
    absolute_numbers_of,
)
from app.episodes.service.records import _record_fields
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source


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
