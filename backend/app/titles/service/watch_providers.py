# TODO: Validate
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, select

from app.models import MediaMixin
from app.titles.models import Title, TitleWatchProvider
from app.titles.schemas import WatchProviderOffering
from app.utils import tz_datetime
from app.watch_providers.models import WatchProvider
from plugins.utils.constants import OUTDATED_STATUS


# TODO: Validate
def _upsert_watch_providers(
    session: Session,
    offerings: Sequence[WatchProviderOffering],
) -> dict[int, uuid.UUID]:
    wanted = {offering.tmdb_provider_id: offering for offering in offerings}
    stored = {
        provider.tmdb_provider_id: provider
        for provider in session.exec(
            select(WatchProvider).where(
                col(WatchProvider.tmdb_provider_id).in_(list(wanted)),
            ),
        ).all()
    }
    for tmdb_provider_id, offering in wanted.items():
        provider = stored.get(tmdb_provider_id)
        if provider is None:
            stored[tmdb_provider_id] = WatchProvider(
                tmdb_provider_id=tmdb_provider_id,
                name=offering.provider_name,
                logo_url=offering.logo_url,
            )
            session.add(stored[tmdb_provider_id])
        elif (provider.name, provider.logo_url) != (
            offering.provider_name,
            offering.logo_url,
        ):
            provider.name = offering.provider_name
            provider.logo_url = offering.logo_url
            session.add(provider)
    session.flush()
    return {
        tmdb_provider_id: provider.id for tmdb_provider_id, provider in stored.items()
    }


# TODO: Validate
def _changed_us_provider_names(
    title: Title,
    offerings: Sequence[WatchProviderOffering],
) -> set[str]:
    stored = {
        row.watch_provider.tmdb_provider_id: row.watch_provider.name
        for row in title.watch_providers
        if row.region == "US"
    }
    wanted = {
        offering.tmdb_provider_id: offering.provider_name
        for offering in offerings
        if offering.region == "US"
    }
    return {
        (wanted | stored)[tmdb_provider_id]
        for tmdb_provider_id in set(stored) ^ set(wanted)
    }


# TODO: Validate
def _mark_outdated(
    session: Session,
    media: MediaMixin[Any],
    update_at: datetime,
) -> None:
    media.set_update_at(update_at)
    if media.update_at is not None:
        media.status = OUTDATED_STATUS
    session.add(media)


# TODO: Validate
def mark_sources_outdated(
    session: Session,
    title: Title,
    provider_names: set[str],
) -> None:
    from app.titles.service.unmatched import plugin_key_for_provider  # noqa: PLC0415

    plugin_keys = {
        plugin_key
        for provider_name in provider_names
        if (plugin_key := plugin_key_for_provider(provider_name)) is not None
    }
    if not plugin_keys:
        return

    update_at = tz_datetime.now()
    for link in title.linked_title_links:
        linked_title = link.linked_title
        if linked_title.source.plugin.key not in plugin_keys:
            continue
        _mark_outdated(session, linked_title, update_at)
        for season in linked_title.active_children:
            _mark_outdated(session, season, update_at)


# TODO: Validate
def record_watch_providers(
    session: Session,
    title: Title,
    offerings: Sequence[WatchProviderOffering],
) -> None:
    changed_names = _changed_us_provider_names(title, offerings)
    provider_ids = _upsert_watch_providers(session, offerings)
    wanted = {
        (
            offering.region,
            provider_ids[offering.tmdb_provider_id],
            offering.offering_type,
        )
        for offering in offerings
    }
    stored = {
        (row.region, row.watch_provider_id, row.offering_type): row
        for row in title.watch_providers
    }
    for key, row in stored.items():
        if key not in wanted:
            title.watch_providers.remove(row)
    for region, watch_provider_id, offering_type in wanted - set(stored):
        title.watch_providers.append(
            TitleWatchProvider(
                title_id=title.id,
                region=region,
                watch_provider_id=watch_provider_id,
                offering_type=offering_type,
            ),
        )
    session.flush()
    mark_sources_outdated(session, title, changed_names)
