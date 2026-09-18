# TODO: Validate

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
        if field not in self._FIELDS.get(model, frozenset()):
            return cast("ColumnElement[Any]", getattr(model_class, field))
        return self._preferring_tmdb(model, field)

    # TODO: Validate
    def _preferring_tmdb(self, model: str, field: str) -> ColumnElement[Any]:
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
        return season_id()

    # TODO: Validate
    def title_id(self) -> ColumnElement[Any]:
        """Return the canonical title the episode belongs to."""
        return cast("ColumnElement[Any]", col(TMDB_TITLE.id))
