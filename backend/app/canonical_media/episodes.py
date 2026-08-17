# TODO: Validate
"""The episodes a row stands for, read as SQL and read off rows in hand.

Which episodes a website's row stands for is `EpisodeCanonicalEpisode` and
nothing else, so every query wanting the episode behind a row reaches it through
that table. A row standing for nothing is the episode itself and answers for
itself, which is what the outer join and the coalesce here are between them
saying.

The entity is taken rather than the class because most of the callers are joins
that reach the same table more than once and so work through `aliased`, and only
the entity knows which of those the column belongs to.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, func

from app.episodes.models import Episode, EpisodeCanonicalEpisode


# TODO: Validate
def canonical_episode_link() -> Any:  # noqa: ANN401 - An alias of the link table.
    """Return an alias of the link table for one query to join through."""
    return aliased(EpisodeCanonicalEpisode)


# TODO: Validate
def links_of(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table.
) -> ColumnElement[bool]:
    """Return the join condition pairing `episode` with the links it carries."""
    return col(link.episode_id) == col(episode.id)


# TODO: Validate
def links_to(
    canonical_episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table.
) -> ColumnElement[bool]:
    """Return the join condition pairing `canonical_episode` with what stands for it."""
    return col(link.canonical_episode_id) == col(canonical_episode.id)


# TODO: Validate
def canonical_episode_id_column(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table, outer joined already.
) -> ColumnElement[UUID]:
    """Return the episode a row stands for, or the row itself where it stands alone.

    A row that stands for nothing is the episode, so the episode it answers to is
    its own id. Reading the link alone leaves those rows as `NULL` and drops them
    out of every comparison the link is used in.
    """
    return func.coalesce(col(link.canonical_episode_id), col(episode.id))


# TODO: Validate
def canonical_id_of(episode: Episode) -> UUID:
    """Return the episode `episode` stands for, which is itself where it stands alone.

    A row standing for more than one has none to give a caller with room for one
    and answers for itself, the same as a row standing for nothing: whichever of
    them was handed back would be as wrong as the other.
    """
    return episode.sole_canonical_episode_id or episode.id
