# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.canonical_media.keys import SHOW_LEVEL, tmdb_id_of
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.schemas import (
    ShowListPublic,
    UnvalidatedLinkedShowOutput,
    UnvalidatedShowOutput,
)
from app.utils import tz_datetime


# TODO: Validate
def validate_show(session: Session, show: Show) -> Show:
    """Settle the canonical shows a `Show` already stands for as the right ones.

    Nothing about what it stands for changes. A row linked to a title is being
    said to really be that title, and a row that is its own record is being said
    to be one TMDB holds no counterpart for, which is one decision about two
    answers and so one column either way.
    """
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def list_unvalidated_shows(session: Session, limit: int) -> list[UnvalidatedShowOutput]:
    """Return every `Show` whose canonical shows no `User` has validated."""
    shows = session.exec(
        Show.select_with_plugin_eager()
        .where(
            col(Show.canonical_show_validated_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(col(Show.name))
        .limit(limit),
    ).all()

    show_ids = [show.id for show in shows]
    episode_counts = dict(
        session.exec(
            select(Season.show_id, func.count(col(Episode.id)))
            .join(Episode, onclause=col(Episode.season_id) == Season.id)
            .where(
                col(Season.show_id).in_(show_ids),
                col(Season.deleted_at).is_(None),
                col(Episode.deleted_at).is_(None),
            )
            .group_by(col(Season.show_id)),
        ).all(),
    )

    return [
        UnvalidatedShowOutput(
            **ShowListPublic.model_validate(show).model_dump(),
            episode_count=episode_counts.get(show.id, 0),
            created_at=show.created_at,
            linked_shows=[
                UnvalidatedLinkedShowOutput(
                    id=link.canonical_show.id,
                    name=link.canonical_show.name,
                    year=link.canonical_show.year,
                    url=link.canonical_show.url,
                    image_url=link.canonical_show.image_url,
                    tmdb_id=tmdb_id_of(link.canonical_show.key, SHOW_LEVEL),
                    note=link.note,
                )
                for link in show.canonical_show_links
            ],
        )
        for show in shows
    ]
