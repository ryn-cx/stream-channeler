# TODO: Validate

from collections.abc import Sequence

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state
from sqlmodel import Session, col, select

from app.seasons.models import Season
from app.shows.models import Show


# TODO: Validate
def preload_episodes(session: Session, shows: Sequence[Show]) -> None:
    unread = [
        show.id
        for show in shows
        if "seasons" in instance_state(show).unloaded
        or any("episodes" in instance_state(season).unloaded for season in show.seasons)
    ]
    if not unread:
        return
    session.exec(
        select(Season)
        .where(col(Season.show_id).in_(unread))
        .options(
            selectinload(Season.episodes),  # type: ignore[arg-type]
        ),
    ).all()
