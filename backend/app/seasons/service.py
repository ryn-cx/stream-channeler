# TODO: Validate


from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInformationSide,
    SeasonOutput,
)
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourceListPublic


# TODO: Validate
def _information_side(
    label: str,
    season: Season,
    show: Show,
) -> SeasonInformationSide:
    return SeasonInformationSide(
        label=label,
        season=SeasonOutput.model_validate(season),
        show=ShowPublic.model_validate(show),
        source=SourceListPublic.model_validate(show.source),
    )
