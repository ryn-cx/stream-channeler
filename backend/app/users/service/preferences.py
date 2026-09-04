# TODO: Validate


from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlmodel import Session

from app.episodes.user_urls import user_episode_url_count
from app.plugins.identifiers import CUSTOM_MEDIA_SOURCE_KEY
from app.sources.service.lookup import (
    OTHER_SOURCE_KEY,
    episode_counts_by_source_id,
    source_keys,
    sources_by_key,
)
from app.users.models import User, UserSourcePreference
from app.users.schemas import (
    SourcePreference,
    SourcePreferenceOutput,
)


# TODO: Validate
def stored_preferences(
    rows: Iterable[UserSourcePreference],
) -> list[SourcePreference]:
    """Convert a user's stored preference rows into ordered `SourcePreference`s."""
    return [
        SourcePreference(source_key=row.source_key, enabled=row.enabled)
        for row in sorted(rows, key=lambda row: row.priority)
    ]


# TODO: Validate
def effective_source_preferences(
    session: Session,
    stored: list[SourcePreference],
) -> list[SourcePreference]:
    """Return the full ordered preference list (every stored source plus `Other`).

    The stored order and enabled flags win for keys that still exist; any source
    key the user has not stored is appended (enabled), and `Other` is guaranteed to
    be present as the final fallback. Unknown/stale keys are dropped.
    """
    stored_by_key = {preference.source_key: preference for preference in stored}
    default_order = [*source_keys(session), OTHER_SOURCE_KEY]
    valid_keys = set(default_order)

    ordered_keys: list[str] = []
    for preference in stored:
        source_key = preference.source_key
        if source_key in valid_keys and source_key not in ordered_keys:
            ordered_keys.append(source_key)
    for key in default_order:
        if key not in ordered_keys:
            ordered_keys.append(key)

    return [
        SourcePreference(
            source_key=key,
            enabled=stored_by_key[key].enabled if key in stored_by_key else True,
        )
        for key in ordered_keys
    ]


# TODO: Validate
def _source_preference_outputs(
    session: Session,
    current_user: User,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Attach each source's stored display name, favicon and episode count."""
    sources = sources_by_key(session)
    counts = episode_counts_by_source_id(session)
    installed_ids = {source.id for source in sources.values()}
    other_count = sum(
        count for source_id, count in counts.items() if source_id not in installed_ids
    )
    custom_media_count = user_episode_url_count(session, current_user)
    outputs: list[SourcePreferenceOutput] = []
    for preference in preferences:
        source = sources.get(preference.source_key)
        if preference.source_key == OTHER_SOURCE_KEY:
            episode_count = other_count
        elif preference.source_key == CUSTOM_MEDIA_SOURCE_KEY:
            episode_count = custom_media_count
        else:
            episode_count = counts.get(source.id, 0) if source else 0
        outputs.append(
            SourcePreferenceOutput(
                source_key=preference.source_key,
                enabled=preference.enabled,
                name=source.name if source else None,
                favicon_url=source.favicon_url if source else None,
                episode_count=episode_count,
            ),
        )
    return outputs


# TODO: Validate
def source_preferences_output(
    session: Session,
    current_user: User,
) -> list[SourcePreferenceOutput]:
    """Return every stored source plus `Other`, in the `User`'s priority order."""
    return _source_preference_outputs(
        session,
        current_user,
        effective_source_preferences(
            session,
            stored_preferences(current_user.source_preferences),
        ),
    )


# TODO: Validate
def replace_source_preferences(
    session: Session,
    current_user: User,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Replace a `User`'s source preferences (priority order plus enabled)."""
    allowed_keys = {*sources_by_key(session), OTHER_SOURCE_KEY}
    seen: set[str] = set()
    for preference in preferences:
        if preference.source_key not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown source {preference.source_key!r}.",
            )
        if preference.source_key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate source {preference.source_key!r}.",
            )
        seen.add(preference.source_key)

    for existing in list(current_user.source_preferences):
        session.delete(existing)
    session.flush()
    for index, preference in enumerate(preferences):
        session.add(
            UserSourcePreference(
                user_id=current_user.id,
                source_key=preference.source_key,
                priority=index,
                enabled=preference.enabled,
            ),
        )
    session.commit()
    session.refresh(current_user)
    return source_preferences_output(session, current_user)
