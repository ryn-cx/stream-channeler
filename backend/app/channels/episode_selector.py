# TODO: Validate
import random
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, literal_column
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.dependencies import get_readable_channels
from app.channels.models import (
    Channel,
    ChannelEpisodeWhiteList,
    ChannelSeasonWhiteList,
    ChannelShow,
)
from app.channels.schemas import ChannelMediaFilter
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000

_MEDIA_MODEL_MAP: dict[str, type[Episode | Season | Show | Source]] = {
    "episode": Episode,
    "season": Season,
    "show": Show,
    "source": Source,
}


class EpisodeQueryBuilder:
    def __init__(
        self,
        session: SessionDep,
        channel: Channel,
        media_filter: ChannelMediaFilter,
        user: CurrentUser | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._media_filter = self._validate_media_filter(media_filter)
        self._channel_ids: list[UUID] = []
        self._compile_channel_ids(channel)

    def _validate_media_filter(
        self,
        media_filter: ChannelMediaFilter,
    ) -> ChannelMediaFilter:
        media_filter.sort_by = [
            sort_key
            for sort_key in media_filter.sort_by
            if self._is_valid_sort_key(sort_key)
        ]
        return media_filter

    def _compile_channel_ids(self, main_channel: Channel) -> None:
        """Compile a list of channels that the user has access to."""
        additional_channels = get_readable_channels(
            self._session,
            self._user,
            self._media_filter.additional_channels,
        )
        self._channel_ids = [main_channel.id, *(x.id for x in additional_channels)]

    def _parse_date_filter(
        self,
        absolute_date: datetime | None,
        relative_days: int | None,
    ) -> datetime | None:
        # The frontend should try to stop both date inputs from being set at the same
        # time so the precedence is arbitrary here.
        if relative_days:
            return tz_datetime.now() - timedelta(days=relative_days)
        return absolute_date

    def get_episodes(self) -> Sequence[Episode]:
        query = self._base_query()
        query = self._join_whitelist_tables(query)
        query = self._join_show_last_watched(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_watched_episodes(query)
        query = self._filter_unwatched_episodes(query)
        query = self._filter_new_shows(query)
        query = self._filter_started_shows(query)
        query = self._filter_by_air_date(query)
        query = self._filter_by_release_date(query)
        query = self._filter_by_duration(query)
        query = self._sort_episodes(query)
        output = self._session.exec(query).all()

        if self._media_filter.randomize_on_last_sort:
            return self._interleave_by_last_sort_value(output)

        episodes = [row[0] for row in output]
        if self._media_filter.rotate_shows_randomly:
            return self._randomly_interleave_episodes(episodes)

        return episodes

    def _randomly_interleave_episodes(self, episodes: list[Episode]) -> list[Episode]:
        # There isn't a good way to implement this in SQL, but it's not too important
        # because the input is already limited to 1,000 entries so the performance of
        # this function is not a major concern.

        # This works by grouping all of the episodes by show then randomly picking a
        # show to take the next episode from until all episodes are added to the output.
        show_episodes: dict[UUID, list[Episode]] = defaultdict(list)
        for episode in episodes:
            show_id = episode.season.show_id
            show_episodes[show_id].append(episode)

        output: list[Episode] = []
        show_lists = list(show_episodes.values())

        while show_lists:
            # S311 - This does not need to be a cryptographically secure
            chosen_list = random.choice(show_lists)  # noqa: S311
            output.append(chosen_list.pop(0))

            if not chosen_list:
                show_lists.remove(chosen_list)

        return output

    def _interleave_by_last_sort_value(
        self,
        results: Sequence[tuple[Episode, Any]],
    ) -> list[Episode]:
        """Interleave episodes based on the last sort value.

        This will group all episodes by the last sort value, and then randomly
        interleave the episodes without changing the order of the episodes within a
        show.

        This is useful when you have a boolean-like filter such as
        value.show.recently_aired_month so you can have a random selection of all of the
        airing episodes before moving on to the non-airing episodes."""
        # Group episodes by the last sort value
        sort_value_groups: dict[str, list[Episode]] = defaultdict(list)
        for row in results:
            episode, sort_value = row
            sort_key = str(sort_value)
            sort_value_groups[sort_key].append(episode)

        # Interleave episodes from each group
        output: list[Episode] = []
        for episodes in sort_value_groups.values():
            interleaved = self._randomly_interleave_episodes(episodes)
            output.extend(interleaved)

        return output

    def get_episode_channels(self, episodes: Sequence[Episode]) -> dict[UUID, UUID]:
        """Get the channel ID for each episode based on the current filter.

        Args:
            episodes: List of episodes to get channel IDs for.

        Returns:
            A dictionary mapping episode IDs to channel IDs.
        """
        query = (
            select(Episode.id, ChannelShow.channel_id)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )
        query = self._join_whitelist_tables(query)
        query = query.where(col(Episode.id).in_([ep.id for ep in episodes]))
        query = query.where(col(ChannelShow.channel_id).in_(self._channel_ids))
        query = self._filter_episodes_by_channels(query)
        results = self._session.exec(query).all()
        return dict(results)

    def _base_query(self) -> Select[tuple[Episode, Any]]:
        if not self._media_filter.sort_by:
            self._media_filter.sort_by.append("value.episode.random.ascending")

        sort_expression = self._get_sorter(self._media_filter.sort_by[-1])

        query = (
            select(Episode, sort_expression.label("primary_sort_value"))
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )
        return query.limit(MAX_EPISODES_RETURNED)

    def _join_whitelist_tables[
        T: Select[tuple[UUID, UUID]] | Select[tuple[Episode, Any]],
    ](
        self,
        query: T,
    ) -> T:
        # return-value - MyPy doesn't understand this but Pylance does.
        return query.outerjoin(  # type: ignore[return-value]
            ChannelSeasonWhiteList,
            and_(
                ChannelSeasonWhiteList.channel_show_id == ChannelShow.id,
                ChannelSeasonWhiteList.season_id == Season.id,
            ),
        ).outerjoin(
            ChannelEpisodeWhiteList,
            and_(
                ChannelEpisodeWhiteList.channel_show_id == ChannelShow.id,
                ChannelEpisodeWhiteList.episode_id == Episode.id,
            ),
        )

    def _join_show_last_watched(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        needs_last_watched = (
            "max.show-episodes.last_watched.descending" in self._media_filter.sort_by
            or "max.show-episodes.last_watched.ascending" in self._media_filter.sort_by
        )
        if not needs_last_watched or not self._user:
            return query

        show_last_watched_subquery = (
            select(
                Season.show_id,
                func.max(Watch.watch_date).label("show_last_watch_date"),
            )
            .select_from(Watch)
            .join(Episode)
            .join(Season)
            .where(
                and_(
                    col(Watch.user_id) == self._user.id,
                    col(Episode.deleted_at).is_(None),
                ),
            )
            .group_by(col(Season.show_id))
            .subquery("show_last_watched")
        )

        return query.outerjoin(
            show_last_watched_subquery,
            col(Show.id) == show_last_watched_subquery.c.show_id,
        )

    def _filter_deleted_media(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return query.where(col(Episode.deleted_at).is_(None))

    def _filter_by_plugin_visibility(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        """Filter out episodes from private plugins the viewer doesn't own."""
        conditions = [col(Plugin.public).is_(True)]
        if self._user:
            conditions.append(col(Plugin.user_id) == self._user.id)
        return (
            query.join(Source, col(Show.source_id) == Source.id)
            .join(
                Plugin,
                col(Source.plugin_id) == Plugin.id,
            )
            .where(or_(*conditions))
        )

    def _filter_episodes_by_channels[
        T: Select[tuple[Episode, Any]] | Select[tuple[UUID, UUID]],
    ](
        self,
        query: T,
    ) -> T:
        # return-value - MyPy doesn't understand this but Pylance does.
        query = query.where(col(ChannelShow.channel_id).in_(self._channel_ids))  # type: ignore[assignment]
        # return-value - MyPy doesn't understand this but Pylance does.
        return query.where(  # type: ignore[return-value]
            or_(
                # Whitelist uses or because if either value is True it should be shown
                and_(
                    col(ChannelShow.white_list_mode).is_(True),
                    or_(
                        col(ChannelSeasonWhiteList.season_id).is_not(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                    ),
                ),
                # Blacklist uses and because if either value is True it should be hidden
                and_(
                    col(ChannelShow.white_list_mode).is_(False),
                    col(ChannelSeasonWhiteList.season_id).is_(None),
                    col(ChannelEpisodeWhiteList.episode_id).is_(None),
                ),
            ),
        )

    def _verified_watches_subquery(self) -> SelectOfScalar[UUID]:
        """Subquery selecting episode IDs with verified watches for the current user."""
        return select(Watch.episode_id).where(
            and_(
                Watch.user_id == self._user.id,  # type: ignore[union-attr]
                col(Watch.verified).is_(True),
            ),
        )

    def _filter_watched_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.hide_watched):
            return query

        watched_subquery = self._verified_watches_subquery()

        absolute_date = self._media_filter.maximum_watch_date_absolute
        relative_date = self._media_filter.maximum_watch_date_relative
        if max_watch_date := self._parse_date_filter(absolute_date, relative_date):
            watched_subquery = watched_subquery.where(
                Watch.watch_date > max_watch_date,
            )

        return query.where(col(Episode.id).not_in(watched_subquery))

    def _filter_unwatched_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.hide_unwatched):
            return query

        return query.where(col(Episode.id).in_(self._verified_watches_subquery()))

    def _started_shows_subquery(self) -> SelectOfScalar[UUID]:
        # This should be impossible because the caller should be checking if user is
        # defined before calling this function.
        if not self._user:
            msg = "Started shows subquery requires a valid user"
            raise ValueError(msg)

        return (
            select(Show.id)
            .join(Season, col(Show.id) == Season.show_id)
            .join(Episode, col(Season.id) == Episode.season_id)
            .join(
                Watch,
                and_(
                    Watch.episode_id == Episode.id,
                    Watch.user_id == self._user.id,
                ),
            )
            .where(col(Watch.verified).is_(True))
            .distinct()
        )

    def _filter_new_shows(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.only_started_shows):
            return query

        return query.where(col(Show.id).in_(self._started_shows_subquery()))

    def _filter_started_shows(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.only_new_shows):
            return query

        return query.where(col(Show.id).not_in(self._started_shows_subquery()))

    def _apply_nullable_range_filter(
        self,
        query: Select[tuple[Episode, Any]],
        column: ColumnElement[Any] | Mapped[Any],
        min_value: datetime | int | None,
        max_value: datetime | int | None,
    ) -> Select[tuple[Episode, Any]]:
        """Apply a min/max range filter that allows NULL values through."""
        if min_value is not None:
            query = query.where(or_(column >= min_value, column.is_(None)))
        if max_value is not None:
            query = query.where(or_(column <= max_value, column.is_(None)))
        return query

    def _filter_by_air_date(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.air_date),
            self._parse_date_filter(
                self._media_filter.minimum_air_date_absolute,
                self._media_filter.minimum_air_date_relative,
            ),
            self._parse_date_filter(
                self._media_filter.maximum_air_date_absolute,
                self._media_filter.maximum_air_date_relative,
            ),
        )

    def _filter_by_release_date(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.release_date),
            self._parse_date_filter(
                self._media_filter.minimum_release_date_absolute,
                self._media_filter.minimum_release_date_relative,
            ),
            self._parse_date_filter(
                self._media_filter.maximum_release_date_absolute,
                self._media_filter.maximum_release_date_relative,
            ),
        )

    def _filter_by_duration(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.duration),
            self._media_filter.minimum_duration,
            self._media_filter.maximum_duration,
        )

    def _collect_sort_expressions(
        self,
        *,
        exclude_show_episodes: bool = False,
    ) -> list[UnaryExpression[Any] | ColumnElement[Any]]:
        """Collect sort expressions from configured sort keys.

        Args:
            exclude_show_episodes: If True, skip show-episodes sort keys (used for
                window function partitioning to avoid nested window functions).
        """
        sort_expressions: list[UnaryExpression[Any] | ColumnElement[Any]] = []
        for sort_key in reversed(self._media_filter.sort_by):
            if exclude_show_episodes and sort_key.split(".")[1] == "show-episodes":
                continue
            sort_expressions.append(self._sql_sort_expression(sort_key))

        return sort_expressions

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        # This will interleave shows in a consistent manner, but it does not actually
        # handle interleaving shows randomly because there is no practical way to
        # implement this in SQL. Instead an interleaved result is returned so that way
        # the random interleaving has an even distribution of episodes for every show.
        # This cannot be implemented in SQL because random interleaving does not
        # interleave based on episodes but individual shows so that way a show with
        # hundreds of episodes does not dominate the result if other shows only have a
        # few episodes. Luckily there is minimal performance concern when interleaving
        # like this because the input for random interleaving is limited to at most
        # 1,000 episodes.
        if (
            self._media_filter.rotate_shows
            or self._media_filter.rotate_shows_randomly
            or self._media_filter.randomize_on_last_sort
        ):
            # This gets around SQLAlchemy putting window functions inside of window
            # definitions when working with a show_series style sort expression and
            # interleaving episodes.
            interleave_partition = func.row_number().over(
                partition_by=col(Show.id),
                order_by=self._collect_sort_expressions(exclude_show_episodes=True),
            )
            return query.order_by(
                interleave_partition,
                *self._collect_sort_expressions(),
            )

        return query.order_by(*self._collect_sort_expressions())

    def _sql_sort_by_value_expression(
        self,
        media_type: str,
        field_name: str,
    ) -> ColumnElement[Any]:
        """Get field for value-based sorting."""
        # Some sorts cannot be done using the simple field accessors.
        if media_type == "show" and field_name == "recently_aired_week":
            return self._recently_airing_sort_expression(7)
        if media_type == "show" and field_name == "recently_aired_month":
            return self._recently_airing_sort_expression(30)
        if media_type == "show" and field_name == "started":
            return self._started_show_sort_expression()

        model = _MEDIA_MODEL_MAP.get(media_type)
        if model is None:
            msg = f"Unsupported media type '{media_type}' for value category"
            raise ValueError(msg)

        # no-any-return - This should always be a ColumnElement because the input values
        # have been validated to be something that returns a ColumnElement.
        return getattr(model, field_name)  # type: ignore[no-any-return]

    def _recently_airing_sort_expression(self, days: int) -> ColumnElement[Any]:
        recent_episode_query = (
            select(Episode.id)
            .join(Season)
            .where(
                and_(
                    col(Season.show_id) == col(Show.id),
                    col(Episode.air_date).is_not(None),
                    col(Episode.air_date) >= tz_datetime.now() - timedelta(days=days),
                    col(Episode.deleted_at).is_(None),
                ),
            )
            .correlate(Show)
            .limit(1)
        )

        return case((recent_episode_query.exists(), 1), else_=0)

    def _started_show_sort_expression(self) -> ColumnElement[Any]:
        if not self._user:
            return literal_column("0")
        started_query = (
            select(Watch.id)
            .join(Episode, Watch.episode_id == Episode.id)
            .join(Season, Episode.season_id == Season.id)
            .where(
                and_(
                    col(Season.show_id) == col(Show.id),
                    Watch.user_id == self._user.id,
                    col(Watch.verified).is_(True),
                ),
            )
            .correlate(Show)
            .limit(1)
        )
        return case((started_query.exists(), 1), else_=0)

    def _sql_sort_by_show_episodes_expression(
        self,
        category: str,
        field_name: str,
    ) -> ColumnElement[Any]:
        """Get aggregate function for show-episodes sorting using window functions."""
        # Some sorts cannot be done using the simple field accessors.
        if field_name == "last_watched":
            return literal_column("show_last_watched.show_last_watch_date")

        if field_name == "random":
            # Hash the show ID with a per-request random salt to produce a uniform,
            # non-deterministic, per-show value. All episodes in a show get the same
            # value since the hash only depends on Show.id and the constant salt.
            # S311 - This does not need to be cryptographically secure.
            salt = str(random.randint(0, 2**31))  # noqa: S311
            episode_field = func.hashtext(
                func.concat(func.cast(Show.id, String), salt),
            )
        else:
            episode_field = getattr(Episode, field_name)
        agg_funcs: dict[str, Any] = {
            "sum": func.sum,
            "avg": func.avg,
            "count": func.count,
            "max": func.max,
            "min": func.min,
            "first_value": func.first_value,
        }
        agg_func = agg_funcs.get(category)
        if agg_func is None:
            msg = f"Unsupported category '{category}' for show-episodes"
            raise ValueError(msg)

        return agg_func(episode_field).over(partition_by=col(Show.id))

    def _get_sorter(
        self,
        sort_key: str,
    ) -> ColumnElement[Any]:
        category, media_type, field_name, _direction = sort_key.split(".")

        # Order matters: show-episodes handles its own "random" case internally,
        # so it must be checked before the generic random handler below.
        if media_type == "show-episodes":
            return self._sql_sort_by_show_episodes_expression(category, field_name)
        if field_name == "random":
            return func.random()
        if category == "value":
            return self._sql_sort_by_value_expression(media_type, field_name)

        msg = f"Unsupported sort key: {category}.{media_type}.{field_name}"
        raise ValueError(msg)

    def _sql_sort_expression(
        self,
        sort_key: str,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        sorter = self._get_sorter(sort_key)
        _category, _media_type, field_name, direction = sort_key.split(".")

        if direction == "descending":
            sorter = desc(sorter)

        # Last watched with ascending should have nulls first because never watched
        # episodes should appear first.
        if field_name == "last_watched" and direction == "ascending":
            sorter = sorter.nulls_first()
        # Any other value should just be shoved at the end.
        else:
            sorter = sorter.nulls_last()

        return sorter

    def _is_valid_sort_key(self, sort_key: str) -> bool:
        parts = sort_key.split(".")
        if len(parts) != 4:  # noqa: PLR2004
            return False

        category, media_type, field_name, direction = parts

        if media_type not in ("show", "season", "episode", "source", "show-episodes"):
            return False

        if direction not in ("ascending", "descending"):
            return False

        if media_type == "show-episodes":
            return self._is_valid_show_episodes_sort_key(category, field_name)
        return self._is_valid_non_show_episodes_sort_key(
            category,
            media_type,
            field_name,
        )

    def _is_valid_show_episodes_sort_key(
        self,
        category: str,
        field_name: str,
    ) -> bool:
        if category not in ("sum", "count", "max", "min", "first_value", "avg"):
            return False

        if field_name == "last_watched":
            return self._user is not None

        if field_name == "random":
            return True

        return field_name in Episode.model_fields

    def _is_valid_non_show_episodes_sort_key(
        self,
        category: str,
        media_type: str,
        field_name: str,
    ) -> bool:
        if category != "value":
            return False

        if field_name == "random":
            return True

        if media_type == "show" and field_name in (
            "recently_aired_week",
            "recently_aired_month",
            "started",
        ):
            return True

        model = _MEDIA_MODEL_MAP.get(media_type)
        if model is None:
            return False

        return field_name in model.model_fields

    def get_episode_latest_watch_date(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, Watch]:
        """Get the latest watch for each episode.

        Args:
            episodes: List of episodes to get channel IDs for.

        Returns:
            A dictionary mapping episode IDs to their latest watch.
        """
        if not self._user or not episodes:
            return {}

        max_dates = (
            select(
                Watch.episode_id,
                func.max(Watch.watch_date).label("max_date"),
            )
            .where(
                and_(
                    col(Watch.episode_id).in_(
                        [episode.id for episode in episodes],
                    ),
                    Watch.user_id == self._user.id,
                ),
            )
            .group_by(col(Watch.episode_id))
            .subquery()
        )

        watches = self._session.exec(
            select(Watch)
            .join(
                max_dates,
                and_(
                    Watch.episode_id == max_dates.c.episode_id,
                    Watch.watch_date == max_dates.c.max_date,
                ),
            )
            .where(Watch.user_id == self._user.id),
        ).all()

        return {watch.episode_id: watch for watch in watches}
