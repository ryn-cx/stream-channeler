# TODO: Validate


from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInformationSide,
)
from app.shows.models import Show


# TODO: Validate
def _information_side(
    label: str,
    season: Season,
    show: Show,
    url: str | None,
) -> SeasonInformationSide:
    return SeasonInformationSide(
        label=label,
        name=season.name,
        season_number=season.season_number,
        sort_order=season.sort_order,
        image_url=season.image_url,
        show_name=show.name,
        url=url,
        key=season.key,
    )
