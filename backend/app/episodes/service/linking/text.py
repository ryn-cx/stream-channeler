# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable


# TODO: Validate
def split_name_parts(text: str) -> list[str]:
    """Split a name that lists several episodes at once into one name per episode."""
    parts = [part.strip() for part in re.split(r"\s*\\\s*|\s+[/|]\s+|[;,]\s+", text)]
    return [part for part in parts if part]


# TODO: Validate
def listing_parts(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\s*\\\s*|\s+[/|]\s+|;\s+", text)]
    return [part for part in parts if part]


# TODO: Validate
def best_scores(scored: Iterable[tuple[uuid.UUID, float]]) -> dict[uuid.UUID, float]:
    """Keep only the highest score each TMDB episode was given."""
    best: dict[uuid.UUID, float] = {}
    for tmdb_episode_id, score in scored:
        if score > best.get(tmdb_episode_id, 0.0):
            best[tmdb_episode_id] = score
    return best
