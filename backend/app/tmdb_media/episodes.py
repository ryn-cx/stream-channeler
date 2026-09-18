# TODO: Validate

from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, func

from app.episodes.models import Episode, EpisodeTmdbEpisode


# TODO: Validate
def tmdb_episode_link() -> Any:  # noqa: ANN401 - An alias of the link table.
    """Return an alias of the link table for one query to join through."""
    return aliased(EpisodeTmdbEpisode)


# TODO: Validate
def links_of(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table.
) -> ColumnElement[bool]:
    """Return the join condition pairing `episode` with the links it carries."""
    return col(link.episode_id) == col(episode.id)


# TODO: Validate
def links_to(
    tmdb_episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table.
) -> ColumnElement[bool]:
    """Return the join condition pairing `tmdb_episode` with what stands for it."""
    return col(link.tmdb_episode_id) == col(tmdb_episode.id)


# TODO: Validate
def tmdb_episode_id_column(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    link: Any,  # noqa: ANN401 - An alias of the link table, outer joined already.
) -> ColumnElement[UUID]:
    return func.coalesce(col(link.tmdb_episode_id), col(episode.id))


# TODO: Validate
def tmdb_record_id_of(episode: Episode) -> UUID:
    return episode.sole_tmdb_episode_id or episode.id
