# TODO: Validate
"""Which website's copy of an episode a `User` watches.

Every website's copy of the same episode points at the same canonical row, so
a channel that holds a title on several sites would otherwise offer the same
episode once per site. The `User`'s source preferences rank the sites, and the
highest-ranked copy is the one that stands for the episode.
"""

from dataclasses import dataclass

from app.auth.dependencies import SessionDep
from app.sources.service import OTHER_SOURCE_KEY
from app.users.models import User
from app.users.service import effective_source_preferences, stored_preferences


# TODO: Validate
@dataclass
class SourceDedupConfig:
    """Resolved priority and enabled state used while selecting episodes."""

    priority: dict[str, int]
    other_priority: int
    disabled_keys: set[str]
    enabled_keys: set[str]
    other_enabled: bool

    # TODO: Validate
    def priority_for(self, source_key: str | None) -> int:
        """Return the priority of a source key, falling back to `Other`."""
        if source_key is None:
            return self.other_priority
        return self.priority.get(source_key, self.other_priority)


# TODO: Validate
def source_dedup_config(
    session: SessionDep,
    user: User | None,
) -> SourceDedupConfig:
    """Resolve a user's effective preferences into priorities and enabled sets."""
    stored = stored_preferences(user.source_preferences) if user else []
    preferences = effective_source_preferences(session, stored)
    priority = {
        preference.source_key: index for index, preference in enumerate(preferences)
    }
    disabled_keys = {
        preference.source_key
        for preference in preferences
        if not preference.enabled and preference.source_key != OTHER_SOURCE_KEY
    }
    enabled_keys = {
        preference.source_key
        for preference in preferences
        if preference.enabled and preference.source_key != OTHER_SOURCE_KEY
    }
    other_enabled = next(
        preference.enabled
        for preference in preferences
        if preference.source_key == OTHER_SOURCE_KEY
    )
    return SourceDedupConfig(
        priority=priority,
        other_priority=priority[OTHER_SOURCE_KEY],
        disabled_keys=disabled_keys,
        enabled_keys=enabled_keys,
        other_enabled=other_enabled,
    )


