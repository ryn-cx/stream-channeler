# TODO: Validate
"""Which website's copy of an episode a `User` watches.

Every website's copy of the same episode carries the same `episode_identifier`, so
a channel that holds a title on several sites would otherwise offer the same
episode once per site. The `User`'s source preferences rank the sites, and the
highest-ranked copy is the one that stands for the episode.
"""

from dataclasses import dataclass
from uuid import UUID

from app.auth.dependencies import SessionDep
from app.episodes.models import Episode
from app.sources.service import OTHER_SOURCE_KEY
from app.users.schemas import SourcePreference
from app.users.service import effective_source_preferences


@dataclass
class SourceDedupConfig:
    """Resolved priority and enabled state used while selecting episodes."""

    priority: dict[str, int]
    other_priority: int
    disabled_keys: set[str]
    enabled_keys: set[str]
    other_enabled: bool

    def priority_for(self, source_key: str | None) -> int:
        """Return the priority of a source key, falling back to `Other`."""
        if source_key is None:
            return self.other_priority
        return self.priority.get(source_key, self.other_priority)


def source_dedup_config(
    session: SessionDep,
    stored: list[SourcePreference],
) -> SourceDedupConfig:
    """Resolve a user's effective preferences into priorities and enabled sets."""
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


def deduplicate_episodes(
    episodes: list[Episode],
    source_key_by_episode_id: dict[UUID, str],
    config: SourceDedupConfig,
) -> list[Episode]:
    """Return `episodes` with no repeated `episode_identifier`.

    Among episodes that share an identifier the highest-priority source wins, while
    the original ordering is preserved by first occurrence.
    """

    def priority(episode: Episode) -> int:
        return config.priority_for(source_key_by_episode_id.get(episode.id))

    best_by_identifier: dict[str, Episode] = {}
    for episode in episodes:
        identifier = episode.episode_identifier
        current = best_by_identifier.get(identifier)
        if current is None or priority(episode) < priority(current):
            best_by_identifier[identifier] = episode

    deduplicated: list[Episode] = []
    seen: set[str] = set()
    for episode in episodes:
        identifier = episode.episode_identifier
        if identifier in seen:
            continue
        seen.add(identifier)
        deduplicated.append(best_by_identifier[identifier])
    return deduplicated
