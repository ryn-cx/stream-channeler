# TODO: Validate
# pyright: reportArgumentType=false

import sys
from collections.abc import Callable

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select

from app.channels.models import ChannelSeasonFilter, ChannelShow
from app.database import engine, load_models
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from app.utils import tz_datetime

logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

import_plugins()
load_models()

MediaModel = Source | Show | Season | Episode


def _get_plugin_key_source(s: Source) -> str:
    return s.plugin.key


def _get_plugin_key_show(s: Show) -> str:
    return s.source.plugin.key


def _get_plugin_key_season(s: Season) -> str:
    return s.show.source.plugin.key


def _get_plugin_key_episode(e: Episode) -> str:
    return e.season.show.source.plugin.key


MODEL_VALUES: dict[
    type[MediaModel],
    tuple[list[type], LoaderOption, Callable[..., str]],
] = {
    Source: (
        [Plugin],
        selectinload(Source.plugin),  # type: ignore[arg-type]
        _get_plugin_key_source,
    ),
    Show: (
        [Source, Plugin],
        selectinload(Show.source).selectinload(Source.plugin),  # type: ignore[arg-type]
        _get_plugin_key_show,
    ),
    Season: (
        [Show, Source, Plugin],
        (
            selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin)  # type: ignore[arg-type]
        ),
        _get_plugin_key_season,
    ),
    Episode: (
        [Season, Show, Source, Plugin],
        (
            selectinload(Episode.season)  # type: ignore[arg-type]
            .selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin)  # type: ignore[arg-type]
        ),
        _get_plugin_key_episode,
    ),
}


def _channel_inclusion_clause() -> ColumnElement[bool]:
    return or_(
        col(ChannelShow.is_whitelist).is_(True)
        & col(ChannelSeasonFilter.season_id).is_not(None),
        col(ChannelShow.is_whitelist).is_(False)
        & col(ChannelSeasonFilter.season_id).is_(None),
    )


def _season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Season to be included in some channel."""
    return (
        select(ChannelShow.id)
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(ChannelShow.show_id) == col(Season.show_id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


def _show_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Show to have a Season included in a channel."""
    return (
        select(Season.id)
        .join(ChannelShow, col(ChannelShow.show_id) == col(Season.show_id))
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(Season.show_id) == col(Show.id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


def _process_outdated_items(media_class: type[MediaModel]) -> None:
    join_chain, load_options, get_plugin_key = MODEL_VALUES[media_class]
    media_type_name = media_class.__name__.lower()
    update_method_name = f"update_{media_type_name}"

    with Session(engine) as session:
        statement = (
            select(media_class)
            .where(
                col(media_class.update_at).is_not(None),
                col(media_class.update_at) < tz_datetime.now(),
                col(media_class.deleted_at).is_(None),
            )
            .order_by(col(media_class.update_at).asc())
        )
        for model in join_chain:
            statement = statement.join(model)
        # Skip items whose Season is not included in any channel. Source is
        # exempt because updating a Source is how new Shows are discovered.
        if media_class is Show:
            statement = statement.where(_show_has_season_in_channel_exists())
        elif media_class in (Season, Episode):
            statement = statement.where(_season_in_channel_exists())
        statement = (
            statement.join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
            .where(User.email == PLUGIN_USER_EMAIL)
            .options(load_options)
        )

        outdated_items = session.exec(statement).all()
        logger.info(f"Found {len(outdated_items)} outdated {media_type_name}")

        updated_count = 0
        for item in outdated_items:
            plugin_key = get_plugin_key(item)
            logger.info(
                f"Updating {media_type_name}: {item.key} (plugin: {plugin_key})",
            )

            for plugin in plugins:
                if plugin.plugin_key() == plugin_key:
                    plugin_instance = plugin(session)

                    try:
                        getattr(plugin_instance, update_method_name)(item)

                        logger.info(
                            f"Successfully updated {media_type_name}: {item.key}",
                        )
                        updated_count += 1

                        session.commit()
                    except Exception:  # noqa: BLE001 - This chould catch ALL exceptions.
                        logger.exception(
                            f"Failed to update {media_type_name}: {item.key}",
                        )
                        # If any error occurs, roll back changes then set update_at at
                        # the maximum possible value to avoid retrying the update until
                        # the issue is resolved.
                        session.rollback()
                        session.refresh(item)
                        item.update_at = tz_datetime.max()
                        session.commit()
                    break
            else:
                logger.error(
                    f"No matching plugin found for {media_type_name}: {item.key} (plugin: {plugin_key})",
                )

        logger.info(
            f"Updated {updated_count} out of {len(outdated_items)} outdated {media_type_name}",
        )


if __name__ == "__main__":
    _process_outdated_items(Source)
    _process_outdated_items(Show)
    _process_outdated_items(Season)
    _process_outdated_items(Episode)

    logger.info("Outdated source update process completed")
