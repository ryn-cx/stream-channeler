# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

from typing import Any

from app.episodes.models import (
    Episode,
)
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodeRecord,
)
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourceListPublic


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
