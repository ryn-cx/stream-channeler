# TODO: Validate

from typing import Any

from pydantic import BaseModel, ValidationError


# TODO: Validate
class TmdbShowExtra(BaseModel):
    tmdb_episode_group_id: str | None = None


# TODO: Validate
class TmdbEpisodeExtra(BaseModel):
    tmdb_season_number: int | None = None
    tmdb_episode_number: int | None = None


# TODO: Validate
def parse_episode_extra(extra: dict[str, Any] | None) -> TmdbEpisodeExtra:
    if not extra:
        return TmdbEpisodeExtra()
    try:
        return TmdbEpisodeExtra.model_validate(extra)
    except ValidationError:
        return TmdbEpisodeExtra()


# TODO: Validate
def dump_episode_extra(
    tmdb_season_number: int | None,
    tmdb_episode_number: int | None,
) -> dict[str, Any]:
    return TmdbEpisodeExtra(
        tmdb_season_number=tmdb_season_number,
        tmdb_episode_number=tmdb_episode_number,
    ).model_dump()


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
