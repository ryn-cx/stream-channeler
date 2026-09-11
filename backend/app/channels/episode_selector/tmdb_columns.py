# TODO: Validate
"""Reading the canonical row from inside the episode query.

Two websites disagree about what a thing is called, when it aired and where in a
season it sits, and sorting or filtering on the stored column alone both goes by
whichever site happened to supply the row and drops every episode whose site
left that value out. The canonical row is the one answer for all of them, so
each level is joined through the pointer the non-canonical row already carries
and read straight off, with no stand-in to fall back to.

Every level is already joined by `EpisodeQueryBuilder`, which reaches all three
to work out which canonical title an episode belongs to and whether that title
holds it, so they are read from there rather than joined again.
"""

from typing import Any, ClassVar, cast

from sqlalchemy import case
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col

from app.channels.episode_selector.tmdb_entities import (
    TMDB_EPISODE,
    TMDB_SEASON,
    TMDB_TITLE,
    season_id,
)
from app.episodes.models import Episode
from app.seasons.models import Season


# TODO: Validate
class TmdbColumns:
    """The canonical row of each media level, joined in so SQL can read it."""

    _MODELS: ClassVar[dict[str, Any]] = {
        "episode": TMDB_EPISODE,
        "season": TMDB_SEASON,
        "title": TMDB_TITLE,
    }

    # What the canonical row of each level holds. Anything else belongs to the
    # non-canonical row and is read from there.
    _FIELDS: ClassVar = {
        "episode": frozenset(
            {
                "name",
                "description",
                "image_url",
                "thumbnail_url",
                "episode_number",
                "duration",
                "air_date",
                "sort_order",
            },
        ),
        "season": frozenset(
            {"name", "season_number", "image_url", "thumbnail_url", "sort_order"},
        ),
        "title": frozenset(
            {"name", "media_type", "description", "image_url", "thumbnail_url"},
        ),
    }

    _NUMBER_FIELDS: ClassVar = {
        "episode": "episode_number",
        "season": "season_number",
    }

    # The non-canonical row standing in for a level whose canonical row is
    # absent. A canonical title is always reached, so only the two levels below it
    # have one.
    _LINKED: ClassVar[dict[str, Any]] = {
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
        return self._preferring_tmdb(model, field)

    # TODO: Validate
    def _preferring_tmdb(self, model: str, field: str) -> ColumnElement[Any]:
        """Return the canonical row's `field`, standing the other one in for it.

        Asked of the row rather than of the value: a canonical row that holds
        nothing under `field` still answers for everything standing for it, and
        only a level with no canonical row at all is one the non-canonical row has
        to answer for.
        """
        tmdb_entity = self._MODELS[model]
        canonical = getattr(tmdb_entity, field)
        linked = self._LINKED.get(model)
        if linked is None:
            return cast("ColumnElement[Any]", canonical)
        return cast(
            "ColumnElement[Any]",
            case(
                (col(tmdb_entity.id).is_(None), getattr(linked, field)),
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
        return self._preferring_tmdb(model, self._NUMBER_FIELDS[model])

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
    def title_id(self) -> ColumnElement[Any]:
        """Return the canonical title the episode belongs to."""
        return cast("ColumnElement[Any]", col(TMDB_TITLE.id))
