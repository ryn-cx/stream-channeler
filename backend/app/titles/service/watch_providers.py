# TODO: Validate
import uuid
from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.titles.models import Title, TitleWatchProvider
from app.titles.schemas import WatchProviderOffering
from app.watch_providers.models import WatchProvider


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
def record_watch_providers(
    session: Session,
    title: Title,
    offerings: Sequence[WatchProviderOffering],
) -> None:
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
