# TODO: Validate
from fastapi import HTTPException
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import Subquery
from sqlmodel import Session, col, func, select

from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.titles.schemas import TitleBrowseOutput, TitlesBrowsePublic
from plugins.utils.manage_plugins import sorted_plugins


# TODO: Validate
def _browsable_plugin(session: Session, plugin_key: str) -> Plugin:
    plugin_classes = [
        plugin_cls
        for plugin_cls in sorted_plugins()
        if plugin_cls.plugin_name() == plugin_key
    ]
    if not plugin_classes or not plugin_classes[0].browsable_titles():
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_key!r} has no titles to browse.",
        )

    plugin = Plugin.get(session, plugin_key)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_key!r} not found.",
        )
    return plugin


# TODO: Validate
def _ranked_listing(plugin: Plugin, search: str | None) -> Subquery:
    ranked = (
        select(
            Title,
            func.row_number()
            .over(partition_by=col(Title.key), order_by=col(Title.id))
            .label("row_number"),
        )
        .join(Source)
        .where(
            Source.plugin_id == plugin.id,
            col(Title.deleted_at).is_(None),
            col(Source.deleted_at).is_(None),
        )
    )
    if search:
        ranked = ranked.where(col(Title.name).ilike(f"%{search}%"))
    return ranked.subquery()


# TODO: Validate
def browse_plugin_titles(
    session: Session,
    plugin_key: str,
    search: str | None,
    offset: int,
    limit: int,
) -> TitlesBrowsePublic:
    plugin = _browsable_plugin(session, plugin_key)
    listing = _ranked_listing(plugin, search)
    title = aliased(Title, listing)
    base = select(title).where(listing.c.row_number == 1)

    total_count = session.exec(select(func.count()).select_from(base.subquery())).one()
    page = base.order_by(listing.c.name, listing.c.id).offset(offset).limit(limit)
    return TitlesBrowsePublic(
        data=[TitleBrowseOutput.model_validate(row) for row in session.exec(page)],
        total_count=total_count,
    )
