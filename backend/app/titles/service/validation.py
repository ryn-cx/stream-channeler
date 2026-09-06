# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.canonical_media.tmdb import (
    get_tmdb_id,
)
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.titles.schemas import (
    TitleListPublic,
    UnvalidatedLinkedTitleOutput,
    UnvalidatedTitleOutput,
)
from app.utils import tz_datetime


# TODO: Validate
def validate_title(session: Session, title: Title) -> Title:
    """Settle the canonical titles a `Title` already stands for as the right ones.

    Nothing about what it stands for changes. A row linked to a title is being
    said to really be that title, and a row that is its own record is being said
    to be one TMDB holds no counterpart for, which is one decision about two
    answers and so one column either way.
    """
    title.canonical_title_validated_at = tz_datetime.now()
    session.add(title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def list_unvalidated_titles(
    session: Session,
    limit: int,
) -> list[UnvalidatedTitleOutput]:
    """Return every `Title` whose canonical titles no `User` has validated."""
    titles = session.exec(
        Title.select_with_plugin_eager()
        .where(
            col(Title.canonical_title_validated_at).is_(None),
            col(Title.deleted_at).is_(None),
        )
        .order_by(col(Title.name))
        .limit(limit),
    ).all()

    title_ids = [title.id for title in titles]
    episode_counts = dict(
        session.exec(
            select(Season.title_id, func.count(col(Episode.id)))
            .join(Episode, onclause=col(Episode.season_id) == Season.id)
            .where(
                col(Season.title_id).in_(title_ids),
                col(Season.deleted_at).is_(None),
                col(Episode.deleted_at).is_(None),
            )
            .group_by(col(Season.title_id)),
        ).all(),
    )

    return [
        UnvalidatedTitleOutput(
            **TitleListPublic.model_validate(title).model_dump(),
            episode_count=episode_counts.get(title.id, 0),
            created_at=title.created_at,
            linked_titles=[
                UnvalidatedLinkedTitleOutput(
                    id=link.canonical_title.id,
                    name=link.canonical_title.name,
                    year=link.canonical_title.year,
                    url=link.canonical_title.url,
                    image_url=link.canonical_title.image_url,
                    tmdb_id=get_tmdb_id(link.canonical_title.key),
                    note=link.note,
                )
                for link in title.canonical_title_links
            ],
        )
        for title in titles
    ]
