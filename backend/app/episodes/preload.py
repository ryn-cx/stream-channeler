# TODO: Validate

from collections.abc import Sequence

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state
from sqlmodel import Session, col, select

from app.seasons.models import Season
from app.titles.models import Title


# TODO: Validate
def DEPRECATED_preload_episodes(session: Session, titles: Sequence[Title]) -> None:
    unread = [
        title.id
        for title in titles
        if "seasons" in instance_state(title).unloaded
        or any(
            "episodes" in instance_state(season).unloaded for season in title.seasons
        )
    ]
    if not unread:
        return
    session.exec(
        select(Season)
        .where(col(Season.title_id).in_(unread))
        .options(
            selectinload(Season.episodes),  # type: ignore[arg-type]
        ),
    ).all()
