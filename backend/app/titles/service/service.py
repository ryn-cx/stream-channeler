# TODO: Validate

from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.channels.service.titles import (
    title_card_summary,
    titles_by_tmdb_record_id,
)
from app.episodes.models import Episode
from app.issue_reports.service.listing import list_title_issue_reports
from app.media.media_type import TMDBMediaType
from app.media.service.updating import update_record
from app.plugins.identifiers import TMDB_PLUGIN_KEY, TMDB_SOURCE_KEY
from app.seasons.models import Season
from app.sources.schemas import SourceListPublic
from app.titles.models import Title
from app.titles.schemas import (
    TitleInformationOutput,
    TitleInformationSide,
    TitleListPublic,
    TitlePublic,
    TitleUpdate,
    TmdbEpisodeGroupOption,
    UnvalidatedLinkedTitleOutput,
    UnvalidatedTitleOutput,
)
from app.titles.service.linking import (
    link_title,
)
from app.tmdb_media.metadata import tmdb_title_of
from app.tmdb_media.models import TmdbEpisodeOrder
from app.tmdb_media.tmdb import (
    get_media_type_and_tmdb_id,
    get_tmdb_id,
)
from app.users.models import User
from app.utils import tz_datetime


# TODO: Validate
def list_tmdb_episode_groups(
    session: Session,
    title: Title,
) -> list[TmdbEpisodeGroupOption]:
    if title.source.key != TMDB_SOURCE_KEY:
        return []

    media_type, _tmdb_id = get_media_type_and_tmdb_id(title.key)
    if media_type is not TMDBMediaType.tv:
        return []

    return [
        TmdbEpisodeGroupOption(
            id=order.tmdb_group_id,
            name=order.name,
            description=order.description,
            group_count=order.group_count,
            episode_count=order.episode_count,
            type=order.type,
        )
        for order in session.exec(
            select(TmdbEpisodeOrder)
            .where(col(TmdbEpisodeOrder.tmdb_title_id) == title.id)
            .order_by(col(TmdbEpisodeOrder.type), col(TmdbEpisodeOrder.name)),
        ).all()
    ]


# TODO: Validate
def update_title_extra(
    session: Session,
    title: Title,
    extra: dict[str, Any] | None,
) -> None:
    """Store `extra` on `title`.

    The one way of setting what a plugin keeps about a title, so that whatever
    setting it has to drag along happens wherever it is set from.
    """
    title.extra = extra or {}
    session.add(title)
    session.commit()


# TODO: Validate
def force_update_title(session: Session, title: Title) -> Title:
    from plugins.utils.manage_plugins import import_plugins, plugins  # noqa: PLC0415

    import_plugins()
    plugin_classes = {plugin.plugin_name(): plugin for plugin in plugins}
    plugin_class = plugin_classes.get(title.source.plugin.key)
    if plugin_class is None:
        message = (
            f"No plugin named {title.source.plugin.key!r} to read the title again."
        )
        raise HTTPException(status_code=422, detail=message)

    logger.info(
        f"Updating title: {title.source.key} - {title.name or title.key} ({title.key})",
    )
    now = tz_datetime.now()
    title.update_at = now
    for season in title.seasons:
        season.update_at = now
        for episode in season.episodes:
            episode.update_at = now
    session.commit()
    update_record(
        session,
        plugin_class(session, title.source.plugin),
        title.source.plugin.key,
        title,
    )
    link_title(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def _title_output(title: Title) -> TitlePublic:
    return TitlePublic.model_validate(title)


# TODO: Validate
def _information_side(label: str, title: Title) -> TitleInformationSide:
    return TitleInformationSide(
        label=label,
        title=TitlePublic.model_validate(title),
        source=SourceListPublic.model_validate(title.source),
    )


# TODO: Validate
def title_information(
    session: Session,
    title: Title,
    current_user: User | None,
) -> TitleInformationOutput:
    """Return what the website and TMDB each say about a `Title`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    source = title.source

    counterpart = tmdb_title_of(session, title)
    tmdb: TitleInformationSide | None = None
    if counterpart:
        tmdb = _information_side(TMDB_PLUGIN_KEY, counterpart)

    websites: list[TitleInformationSide] = []
    if source.key == TMDB_SOURCE_KEY:
        websites = sorted(
            (
                _information_side(website.source.key, website)
                for website in titles_by_tmdb_record_id(session, [title.id])[title.id]
            ),
            key=lambda website: website.label.lower(),
        )

    card_title = counterpart or title
    details, stats = title_card_summary(session, card_title.id)

    return TitleInformationOutput(
        editable=current_user is not None and current_user.is_superuser,
        issue_reports=list_title_issue_reports(session, title.id),
        source=_information_side(
            source.key,
            title,
        ),
        tmdb=tmdb,
        websites=websites,
        details=details,
        stats=stats,
    )


# TODO: Validate
def update_title_record(
    session: Session,
    title: Title,
    title_input: TitleUpdate,
) -> TitlePublic:
    """Write an update to a `Title`.

    Which canonical title this stands for is not something an update writes: it is
    linker's to work out during an import, or a `User`'s to choose through the
    TMDB matching screens, so there is nothing to repoint here.

    `extra` goes through its own service rather than being written with the rest, since
    what a TMDB row keeps there is the episode order the title is read in and changing
    that means reading the title again and matching every non-canonical row of it
    afresh.
    """
    # Before the rest of the update, because what it does depends on the order
    # the title is read in now and the general write would already have replaced
    # it. The same value going down twice writes nothing the second time.
    if "extra" in title_input.model_fields_set:
        update_title_extra(session, title, title_input.extra)
    return _title_output(title_input.update(session, title))


# TODO: Validate
def validate_title(session: Session, title: Title) -> Title:
    title.tmdb_title_validated_at = tz_datetime.now()
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
            col(Title.tmdb_title_validated_at).is_(None),
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
                    id=link.tmdb_title.id,
                    name=link.tmdb_title.name,
                    year=link.tmdb_title.year,
                    url=link.tmdb_title.url,
                    image_url=link.tmdb_title.image_url,
                    tmdb_id=get_tmdb_id(link.tmdb_title.key),
                    note=link.note,
                )
                for link in title.tmdb_title_links
            ],
        )
        for title in titles
    ]
