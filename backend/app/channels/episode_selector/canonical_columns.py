# TODO: Validate
"""Reading the canonical row from inside the episode query.

Two websites disagree about what a thing is called, when it aired and where in a
season it sits, and sorting or filtering on the stored column alone both goes by
whichever site happened to supply the row and drops every episode whose site
left that value out. The canonical row is the one answer for all of them, so
each level is joined through the pointer the non-canonical row already carries
and read straight off, with no stand-in to fall back to.

Every level is already joined by `EpisodeQueryBuilder`, which reaches all three
to work out which canonical show an episode belongs to and whether that show
holds it, so they are read from there rather than joined again.
"""

from typing import Any, ClassVar, cast

from sqlalchemy import case
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col

from app.channels.episode_selector.canonical_entities import (
    CANONICAL_EPISODE,
    CANONICAL_SEASON,
    CANONICAL_SHOW,
    season_id,
)
from app.episodes.models import Episode
from app.seasons.models import Season


# TODO: Validate
class CanonicalColumns:
    """The canonical row of each media level, joined in so SQL can read it."""

    _MODELS: ClassVar[dict[str, Any]] = {
        "episode": CANONICAL_EPISODE,
        "season": CANONICAL_SEASON,
        "show": CANONICAL_SHOW,
    }

    # What the canonical row of each level holds. Anything else belongs to the
    # non-canonical row and is read from there.
    _FIELDS: ClassVar = {
        "episode": frozenset(
            {
                "name",
                "description",
                "image_url",
                "episode_number",
                "duration",
                "air_date",
                "sort_order",
            },
        ),
        "season": frozenset({"name", "season_number", "image_url", "sort_order"}),
        "show": frozenset({"name", "media_type", "description", "image_url"}),
    }

    _NUMBER_FIELDS: ClassVar = {
        "episode": "episode_number",
        "season": "season_number",
    }

    # The non-canonical row standing in for a level whose canonical row is
    # absent. A canonical show is always reached, so only the two levels below it
    # have one.
    _NON_CANONICAL: ClassVar[dict[str, Any]] = {
        "episode": Episode,
        "season": Season,
    }

    # TODO: Validate
    def column(
        self,
        model: str,
        field: str,
        model_class: type[Any],
    ) -> ColumnElement[Any]:
        """Return `field` as the canonical row has it, or as the other one does.

        The canonical row is what every row standing for it resolves to and is the
        one answer for all of them, so it is read first. An episode nothing was
        minted for it to stand for has no canonical row at all, and there its own
        answer is the only one there is rather than one website's among several. A
        field no canonical row holds - a source's name, a plugin's - belongs to
        the non-canonical row and is read from where it is stored.
        """
        if field not in self._FIELDS.get(model, frozenset()):
            return cast("ColumnElement[Any]", getattr(model_class, field))
        return self._preferring_canonical(model, field)

    # TODO: Validate
    def _preferring_canonical(self, model: str, field: str) -> ColumnElement[Any]:
        """Return the canonical row's `field`, standing the other one in for it.

        Asked of the row rather than of the value: a canonical row that holds
        nothing under `field` still answers for everything standing for it, and
        only a level with no canonical row at all is one the non-canonical row has
        to answer for.
        """
        canonical_entity = self._MODELS[model]
        canonical = getattr(canonical_entity, field)
        non_canonical = self._NON_CANONICAL.get(model)
        if non_canonical is None:
            return cast("ColumnElement[Any]", canonical)
        return cast(
            "ColumnElement[Any]",
            case(
                (col(canonical_entity.id).is_(None), getattr(non_canonical, field)),
                else_=canonical,
            ),
        )

    # TODO: Validate
    def number(self, model: str) -> ColumnElement[Any]:
        """Return the number the media is given, or `NULL` where it has none.

        The canonical row's number where there is one, since an order that goes by
        the canonical numbering has to be able to tell a record with no number
        from one that has one, and the non-canonical row's own only where nothing
        was minted for it to stand for.
        """
        return self._preferring_canonical(model, self._NUMBER_FIELDS[model])

    # TODO: Validate
    def episode_season_id(self) -> ColumnElement[Any]:
        """Return the canonical season the episode belongs to.

        Which season an episode is in is the canonical answer rather than the
        website's, since a website can file an episode under a season the
        canonical hierarchy does not, which is what puts a site's finale in
        another site's specials. An episode with no canonical row is in the season
        its own website filed it under, there being no other record of it.
        """
        return season_id()

    # TODO: Validate
    def show_id(self) -> ColumnElement[Any]:
        """Return the canonical show the episode belongs to."""
        return cast("ColumnElement[Any]", col(CANONICAL_SHOW.id))
