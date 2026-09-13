# TODO: Validate

from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.channels.models import ChannelTitle
from app.episodes.models import Episode
from app.issue_reports.service.listing import list_title_issue_reports
from app.media.media_type import TMDBMediaType
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.sources.schemas import SourceListPublic
from app.titles.models import Title, TitleTmdbTitle
from app.titles.schemas import (
    MissingSourceTitleOutput,
    TitleInformationOutput,
    TitleInformationSide,
    TitleListPublic,
    TitlePublic,
    TitleUpdate,
    TmdbEpisodeGroupOption,
    TmdbTitleOutput,
    UnvalidatedLinkedTitleOutput,
    UnvalidatedTitleOutput,
)
from app.titles.service.linking import (
    _old_relink_episodes,
    _old_reread_in_new_order,
)
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.metadata import tmdb_title_of
from app.tmdb_media.tmdb import (
    chosen_group_id,
    dump_extra,
    get_media_type_and_tmdb_id,
    get_tmdb_id,
)
from app.users.models import User
from app.utils import tz_datetime
from plugins.TMDB import TMDB


# TODO: Validate
def list_tmdb_episode_groups(
    session: Session,
    title: Title,
) -> list[TmdbEpisodeGroupOption]:
    """Return the episode orders TMDB holds for `title`, for one to be chosen from.

    Its own endpoint rather than part of reading the title, because it is read off
    a downloaded file and only ever wanted by somebody about to choose an order.
    A row that is not a TMDB series has none, which reads as an empty list rather
    than as an error: there is nothing wrong with a title having no other order.
    """
    if title.source.plugin.key != TMDB_PLUGIN_KEY:
        return []

    media_type, tmdb_id = get_media_type_and_tmdb_id(title.key)
    if media_type is not TMDBMediaType.tv:
        return []

    groups_file = TMDB(session).tv_series_episode_groups_file(tmdb_id)
    if not groups_file.record_content:
        return []

    return [
        TmdbEpisodeGroupOption(
            id=group.id,
            name=group.name,
            description=group.description,
            group_count=group.group_count,
            episode_count=group.episode_count,
            type=group.type,
        )
        for group in groups_file.parsed().results
    ]


# TODO: Validate
def update_title_extra(
    session: Session,
    title: Title,
    extra: dict[str, Any] | None,
) -> None:
    """Store `extra` on `title`, and read the title again where the order changed.

    The one way of setting what a plugin keeps about a title, so that whatever
    setting it has to drag along happens wherever it is set from.

    Changing the episode order is the case that drags something along. The order decides
    which season an episode sits in and what it is numbered, and a non-canonical row is
    matched to an episode by exactly those. The title is read again so the new order is
    written down.
    """
    validate_extra(session, title, extra)

    reordered = chosen_group_id(title.extra) != chosen_group_id(extra)
    title.extra = extra or {}
    session.add(title)

    if reordered:
        _old_reread_in_new_order(session, title)
        _old_relink_episodes(session, title)
    session.commit()


# TODO: Validate
def update_title_episode_group(
    session: Session,
    title: Title,
    group_id: str | None,
) -> None:
    """Read `title` in the episode order `group_id` names, or in its own for none."""
    update_title_extra(session, title, dump_extra(group_id))


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
    plugin_instance = plugin_class(session, title.source.plugin)
    plugin_instance.update_title(title, force=True)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def validate_extra(
    session: Session,
    title: Title,
    extra: dict[str, Any] | None,
) -> None:
    """Raise where `extra` names an episode order TMDB has no record of.

    Choosing an order replaces the title's own seasons with that order's groups,
    so an id naming nothing would leave the title with no seasons at all. The
    check is against the orders TMDB actually holds for this title rather than
    against the shape of the id, since an id that reads right and names another
    title's order is just as empty.

    Only TMDB's own rows carry an order, so a row of any other plugin is left
    alone: `extra` is each plugin's own scratch column and nothing here knows
    what another plugin keeps in it.
    """
    if title.source.plugin.key != TMDB_PLUGIN_KEY:
        return

    group_id = chosen_group_id(extra)
    if group_id is None:
        return

    media_type, tmdb_id = get_media_type_and_tmdb_id(title.key)
    if media_type is not TMDBMediaType.tv:
        message = "A film has no episode orders to be read in."
        raise HTTPException(status_code=422, detail=message)

    groups_file = TMDB(session).tv_series_episode_groups_file(tmdb_id)
    known = (
        {group.id for group in groups_file.parsed().results}
        if groups_file.record_content
        else set()
    )
    if group_id not in known:
        message = f"TMDB holds no episode order {group_id!r} for this title."
        raise HTTPException(status_code=422, detail=message)


# TODO: Validate
def _title_output(title: Title) -> TitlePublic:
    """Return a `Title` as the website that holds it stored it."""
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

    return TitleInformationOutput(
        editable=current_user is not None and current_user.is_superuser,
        issue_reports=list_title_issue_reports(session, title.id),
        source=_information_side(
            source.key,
            title,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def update_title_record(
    session: Session,
    title: Title,
    title_input: TitleUpdate,
) -> TitlePublic:
    """Write an update to a `Title`.

    Which canonical title this stands for is not something an update writes: it is
    linker's to work out during an import, or a `User`'s to settle through the
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
    """Settle the canonical titles a `Title` already stands for as the right ones.

    Nothing about what it stands for changes. A row linked to a title is being
    said to really be that title, and a row that is its own record is being said
    to be one TMDB holds no counterpart for, which is one decision about two
    answers and so one column either way.
    """
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


# TODO: Validate
def list_titles_missing_sources(
    session: Session,
    limit: int,
) -> list[MissingSourceTitleOutput]:
    """Return every canonical TMDB title that no website's row stands for.

    Ordered by how many channels already hold the title, so the gaps that stop
    something playing are the ones a page of this holds.
    """
    channel_count = (
        select(func.count())
        .select_from(ChannelTitle)
        .where(col(ChannelTitle.tmdb_title_id) == Title.id)
        .correlate(Title)
        .scalar_subquery()
        .label("channel_count")
    )
    stands_for_something = (
        select(TitleTmdbTitle)
        .where(col(TitleTmdbTitle.tmdb_title_id) == Title.id)
        .correlate(Title)
        .exists()
    )
    rows = session.exec(
        select(Title, channel_count)
        .join(Source)
        .join(Plugin)
        .where(
            Plugin.key == TMDB_PLUGIN_KEY,
            is_not_linked(Title),
            col(Title.deleted_at).is_(None),
            ~stands_for_something,
        )
        .order_by(channel_count.desc(), col(Title.name))
        .limit(limit),
    ).all()

    title_ids = [title.id for title, _ in rows]
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
        MissingSourceTitleOutput(
            **TmdbTitleOutput.model_validate(title).model_dump(),
            channel_count=channel_count_of_title,
            episode_count=episode_counts.get(title.id, 0),
        )
        for title, channel_count_of_title in rows
    ]
