# TODO: Validate
"""Reading a record as TMDB has it from inside the episode query."""

from typing import Any, ClassVar, cast
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, func, select
from sqlmodel.sql.expression import Select

from app.episodes.models import Episode
from app.media.tmdb_fallback import (
    EPISODE_FALLBACK_FIELDS,
    EPISODE_IDENTIFIER_FIELD,
    SEASON_FALLBACK_FIELDS,
    SEASON_IDENTIFIER_FIELD,
    SHOW_FALLBACK_FIELDS,
    SHOW_IDENTIFIER_FIELD,
    TMDB_PLUGIN_KEY,
)
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


# TODO: Validate
class TMDBFallbackColumns:
    """The TMDB stand-in of each media level, joined in so SQL can read it.

    Two websites disagree about what a thing is called, when it aired and where
    in a season it sits, and sorting or filtering on the stored column alone both
    goes by whichever site happened to supply the copy and drops every episode
    whose site left that value out. Each level is joined to the TMDB media
    standing in for it by the identifier they share and read TMDB first, falling
    back on the website only where TMDB has nothing, which is the same value the
    record is served with.

    A level is only joined when something asks for one of its columns, so a
    channel that sorts on nothing borrowed pays for no extra joins.
    """

    _FALLBACK_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "episode": EPISODE_FALLBACK_FIELDS,
        "season": SEASON_FALLBACK_FIELDS,
        "show": SHOW_FALLBACK_FIELDS,
    }

    _IDENTIFIER_FIELDS: ClassVar[dict[str, str]] = {
        "episode": EPISODE_IDENTIFIER_FIELD,
        "season": SEASON_IDENTIFIER_FIELD,
        "show": SHOW_IDENTIFIER_FIELD,
    }

    # Read on their own rather than coalesced, since an order that goes by TMDB
    # has to be able to tell a record TMDB has no number for from one it does.
    _NUMBER_FIELDS: ClassVar[dict[str, str]] = {
        "episode": "episode_number",
        "season": "season_number",
    }

    # Which season TMDB puts the episode in, which is not always the season the
    # website put its own copy of that episode in.
    _EPISODE_SEASON_FIELDS: ClassVar[tuple[str, ...]] = (
        "season_number",
        "season_identifier",
    )

    # TODO: Validate
    def __init__(self) -> None:
        """Start with nothing joined; each column asked for adds its level."""
        self._subqueries: dict[str, Any] = {}

    # TODO: Validate
    @staticmethod
    def _subquery(model: str) -> Any:  # noqa: ANN401 - A subquery of whichever level was asked for.
        episode = aliased(Episode)
        season = aliased(Season)
        show = aliased(Show)
        source = aliased(Source)
        plugin = aliased(Plugin)

        owners: dict[str, Any] = {"episode": episode, "season": season, "show": show}
        owner = owners[model]
        identifier_field = TMDBFallbackColumns._IDENTIFIER_FIELDS[model]
        number_field = TMDBFallbackColumns._NUMBER_FIELDS.get(model)
        extra_columns: list[Any] = []
        if number_field:
            extra_columns.append(getattr(owner, number_field).label(number_field))
        if model == "episode":
            extra_columns.extend(
                getattr(season, field).label(field)
                for field in TMDBFallbackColumns._EPISODE_SEASON_FIELDS
            )
        statement: Any = select(
            getattr(owner, identifier_field).label("identifier"),
            *(
                getattr(owner, field).label(field)
                for field in TMDBFallbackColumns._FALLBACK_FIELDS[model]
            ),
            *extra_columns,
        ).select_from(owner)

        # Joined down from the level asked for so each join only names tables
        # already in the statement.
        if model == "episode":
            statement = statement.join(season, col(season.id) == col(episode.season_id))
        if model in {"episode", "season"}:
            statement = statement.join(show, col(show.id) == col(season.show_id))

        return (
            statement.join(source, col(source.id) == col(show.source_id))
            .join(plugin, col(plugin.id) == col(source.plugin_id))
            .where(
                plugin.key == TMDB_PLUGIN_KEY,
                col(owner.deleted_at).is_(None),
            )
            .subquery()
        )

    # TODO: Validate
    def column(
        self,
        model: str,
        field: str,
        model_class: type[Any],
    ) -> ColumnElement[Any]:
        """Return `field` as TMDB has it, falling back on what the record stores."""
        own = cast("ColumnElement[Any]", getattr(model_class, field))
        if field == self._NUMBER_FIELDS.get(model):
            return self._preferred_number(model, own)
        if field not in self._FALLBACK_FIELDS.get(model, ()):
            return own
        if model not in self._subqueries:
            self._subqueries[model] = self._subquery(model)
        return func.coalesce(self._subqueries[model].c[field], own)

    # TODO: Validate
    def _preferred_number(
        self,
        model: str,
        own: ColumnElement[Any],
    ) -> ColumnElement[Any]:
        """Return the number TMDB gives the record, or the website's own.

        A season is numbered by the season TMDB puts the episode in rather than by
        the season the website filed it under, since a website can file an episode
        under a season TMDB does not, which is what puts a site's finale in TMDB's
        specials.
        """
        if model == "season":
            return func.coalesce(
                self.episode_season("season_number"),
                self.number("season"),
                own,
            )
        return func.coalesce(self.number(model), own)

    # TODO: Validate
    def number(self, model: str) -> ColumnElement[Any]:
        """Return the number TMDB gives the record, or `NULL` when it has none."""
        field = self._NUMBER_FIELDS[model]
        if model not in self._subqueries:
            self._subqueries[model] = self._subquery(model)
        return self._subqueries[model].c[field]

    # TODO: Validate
    def episode_season(self, field: str) -> ColumnElement[Any]:
        """Return `field` of the season TMDB puts the episode in."""
        if "episode" not in self._subqueries:
            self._subqueries["episode"] = self._subquery("episode")
        return self._subqueries["episode"].c[field]

    # TODO: Validate
    def join(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Join in every level whose columns were asked for."""
        linked: dict[str, Any] = {"episode": Episode, "season": Season, "show": Show}
        for model, subquery in self._subqueries.items():
            identifier = getattr(linked[model], self._IDENTIFIER_FIELDS[model])
            query = query.outerjoin(subquery, identifier == subquery.c.identifier)
        return query
