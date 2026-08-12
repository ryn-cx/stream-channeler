# TODO: Validate
"""Reading the media a copy is of from inside the episode query.

Two websites disagree about what a thing is called, when it aired and where in a
season it sits, and sorting or filtering on the stored column alone both goes by
whichever site happened to supply the copy and drops every episode whose site
left that value out. The canonical row is the one answer for all of them, so
each level is joined through the pointer the copy already carries and read
straight off, with no stand-in to fall back to.

The episode's own canonical row and the season above it are already joined by
`EpisodeQueryBuilder`, which reaches them to work out which title an episode
belongs to, so they are read from there rather than joined again. The title is
only joined when something asks for one of its columns.
"""

from typing import Any, ClassVar, cast
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col
from sqlmodel.sql.expression import Select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode

# The title is aliased so that a query which already reaches `CanonicalShow` for
# its own reasons is never confused with the one joined here. The episode and the
# season are the very rows the query is built around, so they are read as they
# are.
_CanonicalShow = aliased(CanonicalShow)


# TODO: Validate
class CanonicalColumns:
    """The canonical row of each media level, joined in so SQL can read it."""

    _MODELS: ClassVar[dict[str, Any]] = {
        "episode": CanonicalEpisode,
        "season": CanonicalSeason,
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
        """Start with the title unjoined; asking for one of its columns joins it."""
        self._joins_title = False

    # TODO: Validate
    def _require(self, model: str) -> Any:  # noqa: ANN401 - The canonical model of whichever level was asked for.
        """Mark the title as needing to be joined, when that is what was asked for."""
        if model == "show":
            self._joins_title = True
        return self._MODELS[model]

    # TODO: Validate
    def column(
        self,
        model: str,
        field: str,
        model_class: type[Any],
    ) -> ColumnElement[Any]:
        """Return `field` as the canonical row has it.

        Read off the canonical row alone rather than falling back on the copy: the
        canonical row is what every copy resolves to and it is never absent, so a
        fallback could only ever put one website's answer in place of the one
        answer for all of them. A field no canonical row holds - a source's name,
        a plugin's - is the copy's own and is read from where it is stored.
        """
        if field not in self._FIELDS.get(model, frozenset()):
            return cast("ColumnElement[Any]", getattr(model_class, field))
        canonical = self._require(model)
        return cast("ColumnElement[Any]", getattr(canonical, field))

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
        """Join in the title, when one of its columns was asked for.

        The episode and the season it is in are what the query is built around
        and are already there. The title is one join further out and nothing but
        its own columns needs it, so it is only reached for when asked for.
        """
        if self._joins_title:
            query = query.join(
                _CanonicalShow,
                col(CanonicalSeason.canonical_show_id) == col(_CanonicalShow.id),
            )
        return query
