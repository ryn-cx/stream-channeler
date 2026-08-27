# TODO: Validate
"""Which of TMDB's episode orders a title is read in.

TMDB numbers a series the way the network first aired it, and keeps the other
ways of ordering it - the DVD order, the story order, the order a streaming
service uses - as episode groups beside it. A title whose website follows one of
those is a title nothing lines up against until the same order is read here, so
one can be chosen and stored against the `Show`.

The choice lives in the `Show`'s `extra`, which is where a plugin keeps what the
columns have no room for. It is written as an object rather than the bare id so
that a second thing TMDB needs saying about a title has somewhere to go without
the meaning of what is already stored changing.

An order that is chosen replaces the title's own: the groups become its seasons
and their episodes are numbered as the order numbers them. That is why the id is
checked against the orders TMDB actually holds for the title before it is
stored - an id naming nothing would leave a title with no seasons at all.
"""

from typing import Any

from pydantic import BaseModel, ValidationError


# TODO: Validate
class TmdbShowExtra(BaseModel):
    """What TMDB keeps about a title beyond the columns of the row."""

    tmdb_episode_group_id: str | None = None


# TODO: Validate
def parse_extra(extra: dict[str, Any] | None) -> TmdbShowExtra:
    """Return what `extra` says, or an empty answer where it says nothing.

    Anything that is not of this shape is read as saying nothing rather than
    raising, since `extra` is shared with whatever else a plugin keeps there and
    a row written before this existed is a row to be read, not a failure.
    """
    if not extra:
        return TmdbShowExtra()
    try:
        return TmdbShowExtra.model_validate(extra)
    except ValidationError:
        return TmdbShowExtra()


# TODO: Validate
def chosen_group_id(extra: dict[str, Any] | None) -> str | None:
    """Return the episode order a title is read in, where one was chosen."""
    return parse_extra(extra).tmdb_episode_group_id


# TODO: Validate
def dump_extra(group_id: str | None) -> dict[str, Any]:
    """Return what to store in `extra` for a title read in `group_id`'s order.

    An empty object rather than one naming nothing, so a title put back to TMDB's
    own order is stored the way a title that was never moved off it is.
    """
    if not group_id:
        return {}
    return TmdbShowExtra(tmdb_episode_group_id=group_id).model_dump()
