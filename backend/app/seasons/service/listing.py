# TODO: Validate


from typing import Any

from sqlmodel import Session

from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonListOutput,
    SeasonsPublic,
)
from app.service.responses import list_response
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.key,
}


# TODO: Validate
def season_list_output(
    session: Session,
    current_user: User,
    read_options: ReadOptions,
) -> SeasonsPublic:
    """Read one page of every `Season`."""
    return list_response(
        session=session,
        base=Season.select_with_plugin_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
