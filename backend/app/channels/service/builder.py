# TODO: Validate


import uuid
from collections import defaultdict
from collections.abc import Collection, Sequence

from sqlmodel import Session, col, select

from app.channels.models import Channel
from app.channels.schemas import ChannelBuildPlugin
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.titles import add_tmdb_titles_to_channel
from app.plugins.models import Plugin
from app.schemas import Message
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.tmdb import is_tmdb_key
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import get_plugin_from_url, sorted_plugins


# TODO: Validate
def _plugin_class(plugin_key: str) -> type[AbstractPlugin] | None:
    for plugin_class in sorted_plugins():
        if plugin_class.plugin_name() == plugin_key:
            return plugin_class
    return None


# TODO: Validate
def _titles_to_ask(tmdb_title: Title) -> list[Title]:
    titles = [
        link.linked_title
        for link in tmdb_title.linked_title_links
        if link.linked_title.deleted_at is None
    ]
    if is_tmdb_key(tmdb_title.key):
        titles.append(tmdb_title)
    return titles


# TODO: Validate
def _asks_similar(title: Title) -> type[AbstractPlugin] | None:
    plugin_class = _plugin_class(title.source.plugin.key)
    if plugin_class is None or not plugin_class.implements("similar_title_urls"):
        return None
    return plugin_class


# TODO: Validate
def similar_title_urls(
    session: Session,
    tmdb_title: Title,
    plugin_keys: Collection[str] | None = None,
) -> list[str]:
    urls: list[str] = []
    for title in _titles_to_ask(tmdb_title):
        plugin_class = _asks_similar(title)
        if plugin_class is None:
            continue
        if plugin_keys is not None and plugin_class.plugin_name() not in plugin_keys:
            continue
        urls.extend(plugin_class(session).similar_title_urls(title))
    return list(dict.fromkeys(urls))


# TODO: Validate
def buildable_plugins(session: Session, title: Title) -> list[ChannelBuildPlugin]:
    plugins: dict[str, ChannelBuildPlugin] = {}
    for tmdb_title in _tmdb_titles(session, title):
        for linked_title in _titles_to_ask(tmdb_title):
            plugin_class = _asks_similar(linked_title)
            if plugin_class is None:
                continue
            plugins.setdefault(
                plugin_class.plugin_name(),
                ChannelBuildPlugin(
                    key=plugin_class.plugin_name(),
                    favicon_url=linked_title.source.favicon_url,
                ),
            )
    return list(plugins.values())


# TODO: Validate
def _canonical_ids_by_plugin_and_key(
    session: Session,
    keys: Collection[str],
) -> dict[tuple[str, str], set[uuid.UUID]]:
    if not keys:
        return {}
    rows = session.exec(
        select(
            Plugin.key,
            Title.key,
            Title.id,
            TitleTmdbTitle.tmdb_title_id,
        )
        .join(Source, col(Title.source_id) == col(Source.id))
        .join(Plugin, col(Source.plugin_id) == col(Plugin.id))
        .outerjoin(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .where(col(Title.key).in_(keys), col(Title.deleted_at).is_(None)),
    ).all()

    canonical_ids: dict[tuple[str, str], set[uuid.UUID]] = defaultdict(set)
    for plugin_key, title_key, title_id, tmdb_title_id in rows:
        canonical_ids[(plugin_key, title_key)].add(tmdb_title_id or title_id)
    return canonical_ids


# TODO: Validate
def _split_urls_by_what_is_imported(
    session: Session,
    urls: Sequence[str],
) -> tuple[set[uuid.UUID], list[str]]:
    instances: dict[type[AbstractPlugin], AbstractPlugin] = {}
    keys_by_url: dict[str, tuple[str, str]] = {}
    for url in urls:
        plugin_class = get_plugin_from_url(url)
        if plugin_class is None or not plugin_class.implements("title_key_from_url"):
            continue
        if plugin_class not in instances:
            instances[plugin_class] = plugin_class(session)
        keys_by_url[url] = (
            plugin_class.plugin_name(),
            instances[plugin_class].title_key_from_url(url),
        )

    canonical_ids = _canonical_ids_by_plugin_and_key(
        session,
        {title_key for _, title_key in keys_by_url.values()},
    )
    tmdb_title_ids: set[uuid.UUID] = set()
    unimported_urls: list[str] = []
    for url in urls:
        found = canonical_ids.get(keys_by_url.get(url, ("", "")))
        if found:
            tmdb_title_ids |= found
        else:
            unimported_urls.append(url)
    return tmdb_title_ids, unimported_urls


# TODO: Validate
def _tmdb_titles(session: Session, title: Title) -> Sequence[Title]:
    tmdb_title_ids = set(title.tmdb_title_ids) or {title.id}
    return session.exec(
        select(Title).where(col(Title.id).in_(tmdb_title_ids)),
    ).all()


# TODO: Validate
def build_from_title(
    session: Session,
    channel: Channel,
    title: Title,
    plugin_keys: Collection[str] | None = None,
) -> Message:
    tmdb_title_ids = set(title.tmdb_title_ids) or {title.id}
    tmdb_titles = _tmdb_titles(session, title)

    urls = list(
        dict.fromkeys(
            url
            for tmdb_title in tmdb_titles
            for url in similar_title_urls(session, tmdb_title, plugin_keys)
        ),
    )
    similar_title_ids, unimported_urls = _split_urls_by_what_is_imported(session, urls)

    added = add_tmdb_titles_to_channel(
        session,
        channel,
        tmdb_title_ids | similar_title_ids,
    )
    add_urls_to_channel_import_queue(session, channel, unimported_urls)
    return Message(
        message=(
            f"{added} titles added to the channel, "
            f"{len(unimported_urls)} URLs added to the import queue"
        ),
    )
