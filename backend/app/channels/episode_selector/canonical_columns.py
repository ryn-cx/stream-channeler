# TODO: Validate
"""Reading the media a copy is of from inside the episode query.

Two websites disagree about what a thing is called, when it aired and where in a
season it sits, and sorting or filtering on the stored column alone both goes by
whichever site happened to supply the copy and drops every episode whose site
left that value out. The canonical row is the one answer for all of them, so
each level is joined through the pointer the copy already carries and read
straight off, with no stand-in to fall back to.

A level is only joined when something asks for one of its columns, and asking
for a level joins the ones above it, since that is the path to reach it.
"""

from typing import Any, ClassVar, cast
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, func
from sqlmodel.sql.expression import Select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode

# Aliased so that a query which already reaches the canonical tables for its own
# reasons is never confused with the levels joined here.
_CanonicalEpisode = aliased(CanonicalEpisode)
_CanonicalSeason = aliased(CanonicalSeason)
_CanonicalShow = aliased(CanonicalShow)


# TODO: Validate
class CanonicalColumns:
    """The canonical row of each media level, joined in so SQL can read it."""

    _MODELS: ClassVar[dict[str, Any]] = {
        "episode": _CanonicalEpisode,
        "season": _CanonicalSeason,
        "show": _CanonicalShow,
    }

    # What the canonical row of each level holds. Anything else is the copy's
    # own and is read from the copy.
    _FIELDS: ClassVar[dict[str, frozenset[str]]] = {
        "episode": frozenset(
            {
                "name",
                "description",
                "image_url",
                "episode_number",
                "duration",
                "release_date",
                "air_date",
                "sort_order",
            },
        ),
        "season": frozenset({"name", "season_number", "image_url", "sort_order"}),
        "show": frozenset({"name", "media_type", "description", "image_url", "icon"}),
    }

    _NUMBER_FIELDS: ClassVar[dict[str, str]] = {
        "episode": "episode_number",
        "season": "season_number",
    }

    # TODO: Validate
    def __init__(self) -> None:
        """Start with nothing joined; each column asked for adds its level."""
        self._levels: set[str] = set()

    # TODO: Validate
    def _require(self, model: str) -> Any:  # noqa: ANN401 - The canonical model of whichever level was asked for.
        """Mark `model` and everything above it as needing to be joined."""
        if model == "show":
            self._levels.update({"episode", "season", "show"})
        elif model == "season":
            self._levels.update({"episode", "season"})
        else:
            self._levels.add("episode")
        return self._MODELS[model]

    # TODO: Validate
    def column(
        self,
        model: str,
        field: str,
        model_class: type[Any],
    ) -> ColumnElement[Any]:
        """Return `field` as the canonical row has it, or the copy's own."""
        own = cast("ColumnElement[Any]", getattr(model_class, field))
        if field not in self._FIELDS.get(model, frozenset()):
            return own
        canonical = self._require(model)
        # Coalesced against the copy so a row whose pointer has not been filled
        # in yet still reads as what it stores rather than as nothing.
        return func.coalesce(getattr(canonical, field), own)

    # TODO: Validate
    def number(self, model: str) -> ColumnElement[Any]:
        """Return the number the canonical row gives, or `NULL` when it has none.

        Read on its own rather than coalesced, since an order that goes by the
        canonical numbering has to be able to tell a record with no number from
        one that has one.
        """
        canonical = self._require(model)
        return getattr(canonical, self._NUMBER_FIELDS[model])

    # TODO: Validate
    def episode_season_id(self) -> ColumnElement[Any]:
        """Return the canonical season the episode belongs to.

        Which season an episode is in is the canonical answer rather than the
        website's, since a website can file an episode under a season the
        canonical hierarchy does not, which is what puts a site's finale in
        another site's specials.
        """
        canonical = self._require("episode")
        return col(canonical.canonical_season_id)

    # TODO: Validate
    def show_id(self) -> ColumnElement[Any]:
        """Return the canonical title the episode belongs to."""
        canonical = self._require("season")
        return col(canonical.canonical_show_id)

    # TODO: Validate
    def join(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Join in every level whose columns were asked for.

        Outer joins throughout: a copy whose pointer is not filled in yet still
        belongs in the results, reading as whatever it stores itself.
        """
        if "episode" in self._levels:
            query = query.outerjoin(
                _CanonicalEpisode,
                col(Episode.canonical_episode_id) == col(_CanonicalEpisode.id),
            )
        if "season" in self._levels:
            query = query.outerjoin(
                _CanonicalSeason,
                col(_CanonicalEpisode.canonical_season_id) == col(_CanonicalSeason.id),
            )
        if "show" in self._levels:
            query = query.outerjoin(
                _CanonicalShow,
                col(_CanonicalSeason.canonical_show_id) == col(_CanonicalShow.id),
            )
        return query
