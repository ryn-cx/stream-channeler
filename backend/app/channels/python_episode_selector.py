# TODO: Validate
import random
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlmodel import and_, col, func, select

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
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000


class PythonEpisodeQueryBuilder:
    """Episode selector that performs filtering and sorting in Python rather than SQL."""

    def __init__(
        self,
        session: SessionDep,
        channel: Channel,
        media_filter: ChannelMediaFilter,
        user: CurrentUser | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._media_filter = self._sanitize_media_filter(media_filter)
        self._channel_ids: list[UUID] = []
        self._compile_channel_ids(channel)
        self._episode_watches: dict[UUID, Watch] = {}
        self._show_last_watched: dict[UUID, datetime] = {}

    @property
    def _effective_seed(self) -> int:
        """Return the explicit seed, or a stable per-channel default derived from its ID."""
        if self._media_filter.random_seed is not None:
            return self._media_filter.random_seed
        return int(str(self._channel_ids[0]).replace("-", "")[:8], 16) % (2**31)

    def _sanitize_media_filter(
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
        # Fetch all episodes with relationships
        episodes = self._fetch_all_episodes()

        # Pre-load watch data if needed
        if self._user:
            self._load_watch_data([ep for ep, _, _, _ in episodes])

        # Filter episodes
        filtered = []
        for episode, season, show, channel_show in episodes:
            if not self._should_include_episode(episode, season, show, channel_show):
                continue
            filtered.append((episode, season, show, channel_show))

        # Sort episodes
        sorted_episodes = self._sort_episodes_python(filtered)

        # Apply interleaving if needed
        if self._media_filter.randomize_on_last_sort:
            return self._interleave_by_last_sort_value_python(sorted_episodes)

        if self._media_filter.rotate_shows_randomly:
            return self._randomly_interleave_episodes(
                [ep for ep, _, _, _ in sorted_episodes],
            )

        return [ep for ep, _, _, _ in sorted_episodes][:MAX_EPISODES_RETURNED]

    def _fetch_all_episodes(
        self,
    ) -> list[tuple[Episode, Season, Show, ChannelShow]]:
        """Fetch all episodes with their relationships for the channels."""
        query = (
            select(Episode, Season, Show, ChannelShow)
            .join(Season, Episode.season_id == Season.id)
            .join(Show, Season.show_id == Show.id)
            .join(
                ChannelShow,
                and_(
                    ChannelShow.show_id == Show.id,
                    col(ChannelShow.channel_id).in_(self._channel_ids),
                ),
            )
            .outerjoin(
                ChannelSeasonWhiteList,
                and_(
                    ChannelSeasonWhiteList.channel_show_id == ChannelShow.id,
                    ChannelSeasonWhiteList.season_id == Season.id,
                ),
            )
            .outerjoin(
                ChannelEpisodeWhiteList,
                and_(
                    ChannelEpisodeWhiteList.channel_show_id == ChannelShow.id,
                    ChannelEpisodeWhiteList.episode_id == Episode.id,
                ),
            )
            .where(col(Episode.deleted_at).is_(None))
            .where(
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
        )

        results = self._session.exec(query).all()
        return [(ep, season, show, cs) for ep, season, show, cs in results]

    def _load_watch_data(self, episodes: list[Episode]) -> None:
        """Pre-load watch data for episodes and shows."""
        if not self._user or not episodes:
            return

        episode_ids = [ep.id for ep in episodes]

        # Load episode watches
        watches = self._session.exec(
            select(Watch).where(
                and_(
                    col(Watch.episode_id).in_(episode_ids),
                    Watch.user_id == self._user.id,
                ),
            ),
        ).all()

        self._episode_watches = {watch.episode_id: watch for watch in watches}

        # Load show last watched dates
        show_ids = list({ep.season.show_id for ep in episodes})
        show_watches = self._session.exec(
            select(Season.show_id, func.max(Watch.watch_date))
            .join(Episode, Episode.season_id == Season.id)
            .join(Watch, Watch.episode_id == Episode.id)
            .where(
                and_(
                    col(Season.show_id).in_(show_ids),
                    Watch.user_id == self._user.id,
                    col(Episode.deleted_at).is_(None),
                ),
            )
            .group_by(Season.show_id),
        ).all()

        self._show_last_watched = {
            show_id: watch_date for show_id, watch_date in show_watches
        }

    def _should_include_episode(
        self,
        episode: Episode,
        season: Season,
        show: Show,
        channel_show: ChannelShow,
    ) -> bool:
        """Check if an episode should be included based on all filters."""
        # Whitelist/blacklist is now handled in SQL

        # Check watched filter
        if not self._check_watched_filter(episode):
            return False

        # Check unwatched filter
        if not self._check_unwatched_filter(episode):
            return False

        # Check new/started shows filters
        if not self._check_new_started_filters(show):
            return False

        # Check air date filters
        if not self._check_air_date_filter(episode):
            return False

        # Check release date filters
        if not self._check_release_date_filter(episode):
            return False

        # Check duration filters
        if not self._check_duration_filter(episode):
            return False

        return True

    def _check_whitelist(
        self,
        episode: Episode,
        season: Season,
        channel_show: ChannelShow,
    ) -> bool:
        """Check if episode passes whitelist/blacklist rules."""
        # Get whitelist entries for this channel_show
        season_whitelist = self._session.exec(
            select(ChannelSeasonWhiteList).where(
                and_(
                    ChannelSeasonWhiteList.channel_show_id == channel_show.id,
                    ChannelSeasonWhiteList.season_id == season.id,
                ),
            ),
        ).first()

        episode_whitelist = self._session.exec(
            select(ChannelEpisodeWhiteList).where(
                and_(
                    ChannelEpisodeWhiteList.channel_show_id == channel_show.id,
                    ChannelEpisodeWhiteList.episode_id == episode.id,
                ),
            ),
        ).first()

        if channel_show.white_list_mode:
            # Whitelist mode: must be in either season or episode whitelist
            return season_whitelist is not None or episode_whitelist is not None
        # Blacklist mode: must not be in either season or episode blacklist
        return season_whitelist is None and episode_whitelist is None

    def _check_watched_filter(self, episode: Episode) -> bool:
        """Check if episode should be hidden based on watched status."""
        if not (self._user and self._media_filter.hide_watched):
            return True

        watch = self._episode_watches.get(episode.id)
        if not watch or not watch.verified:
            return True

        # Check if watch date is within allowed range
        absolute_date = self._media_filter.maximum_watch_date_absolute
        relative_date = self._media_filter.maximum_watch_date_relative
        if max_watch_date := self._parse_date_filter(absolute_date, relative_date):
            return watch.watch_date <= max_watch_date

        return False

    def _check_unwatched_filter(self, episode: Episode) -> bool:
        """Check if episode should be hidden based on unwatched status."""
        if not (self._user and self._media_filter.hide_unwatched):
            return True

        watch = self._episode_watches.get(episode.id)
        return watch is not None and watch.verified

    def _check_new_started_filters(self, show: Show) -> bool:
        """Check if show passes new/started filters."""
        if not self._user:
            return True

        show_started = show.id in self._get_started_show_ids()

        if self._media_filter.only_started_shows and not show_started:
            return False

        if self._media_filter.only_new_shows and show_started:
            return False

        return True

    def _get_started_show_ids(self) -> set[UUID]:
        """Get set of show IDs that have been started by the user."""
        if not self._user:
            return set()

        if not hasattr(self, "_started_show_ids"):
            started_shows = self._session.exec(
                select(Show.id)
                .join(Season, Season.show_id == Show.id)
                .join(Episode, Episode.season_id == Season.id)
                .join(Watch, Watch.episode_id == Episode.id)
                .where(
                    and_(
                        Watch.user_id == self._user.id,
                        col(Watch.verified).is_(True),
                    ),
                )
                .distinct(),
            ).all()
            self._started_show_ids = set(started_shows)

        return self._started_show_ids

    def _check_air_date_filter(self, episode: Episode) -> bool:
        """Check if episode passes air date filters."""
        absolute_date = self._media_filter.minimum_air_date_absolute
        relative_date = self._media_filter.minimum_air_date_relative
        if min_air_date := self._parse_date_filter(absolute_date, relative_date):
            if episode.air_date is not None and episode.air_date < min_air_date:
                return False

        absolute_date = self._media_filter.maximum_air_date_absolute
        relative_date = self._media_filter.maximum_air_date_relative
        if max_air_date := self._parse_date_filter(absolute_date, relative_date):
            if episode.air_date is not None and episode.air_date > max_air_date:
                return False

        return True

    def _check_release_date_filter(self, episode: Episode) -> bool:
        """Check if episode passes release date filters."""
        absolute_date = self._media_filter.minimum_release_date_absolute
        relative_date = self._media_filter.minimum_release_date_relative
        if min_release_date := self._parse_date_filter(absolute_date, relative_date):
            if (
                episode.release_date is not None
                and episode.release_date < min_release_date
            ):
                return False

        absolute_date = self._media_filter.maximum_release_date_absolute
        relative_date = self._media_filter.maximum_release_date_relative
        if max_release_date := self._parse_date_filter(absolute_date, relative_date):
            if (
                episode.release_date is not None
                and episode.release_date > max_release_date
            ):
                return False

        return True

    def _check_duration_filter(self, episode: Episode) -> bool:
        """Check if episode passes duration filters."""
        if self._media_filter.minimum_duration:
            if (
                episode.duration is not None
                and episode.duration < self._media_filter.minimum_duration
            ):
                return False

        if self._media_filter.maximum_duration:
            if (
                episode.duration is not None
                and episode.duration > self._media_filter.maximum_duration
            ):
                return False

        return True

    def _sort_episodes_python(
        self,
        episodes: list[tuple[Episode, Season, Show, ChannelShow]],
    ) -> list[tuple[Episode, Season, Show, ChannelShow]]:
        """Sort episodes using Python sorting instead of SQL ORDER BY."""
        if not self._media_filter.sort_by:
            return episodes

        # Handle interleaving
        if (
            self._media_filter.rotate_shows
            or self._media_filter.rotate_shows_randomly
            or self._media_filter.randomize_on_last_sort
        ):
            # First sort within each show
            show_episodes: dict[
                UUID,
                list[tuple[Episode, Season, Show, ChannelShow]],
            ] = defaultdict(list)
            for item in episodes:
                show_id = item[2].id
                show_episodes[show_id].append(item)

            # Sort episodes within each show
            for show_id in show_episodes:
                show_episodes[show_id] = self._sort_by_keys(
                    show_episodes[show_id],
                    skip_show_episodes=True,
                )

            # Interleave shows
            result = []
            show_lists = list(show_episodes.values())
            while show_lists:
                for show_list in show_lists[:]:
                    if show_list:
                        result.append(show_list.pop(0))
                    if not show_list:
                        show_lists.remove(show_list)

            return result
        return self._sort_by_keys(episodes, skip_show_episodes=False)

    def _sort_by_keys(
        self,
        episodes: list[tuple[Episode, Season, Show, ChannelShow]],
        skip_show_episodes: bool = False,
    ) -> list[tuple[Episode, Season, Show, ChannelShow]]:
        """Sort episodes by the configured sort keys."""
        # Apply sorts in reverse order so the last sort becomes primary
        for sort_key in reversed(self._media_filter.sort_by):
            if skip_show_episodes and sort_key.split(".")[1] == "show-episodes":
                continue

            episodes = sorted(
                episodes,
                key=lambda x: self._get_sort_value(x, sort_key),
                reverse=(sort_key.endswith(".descending")),
            )

        return episodes

    def _get_sort_value(
        self,
        item: tuple[Episode, Season, Show, ChannelShow],
        sort_key: str,
    ) -> Any:
        """Get the sort value for an episode based on the sort key."""
        episode, season, show, channel_show = item
        category, media_type, field_name, direction = sort_key.split(".")

        # Handle show-episodes aggregations
        if media_type == "show-episodes":
            return self._get_show_episodes_sort_value(show, category, field_name)

        # Handle random sorting
        if field_name == "random":
            # Use a stable hash of episode ID + effective seed for deterministic order
            return hash((str(episode.id), self._effective_seed))

        # Handle special show fields
        if media_type == "show":
            if field_name == "recently_aired_week":
                return self._show_recently_aired(show, 7)
            if field_name == "recently_aired_month":
                return self._show_recently_aired(show, 30)

        # Handle regular fields
        obj_map = {
            "episode": episode,
            "season": season,
            "show": show,
            "source": None,  # Would need to be loaded separately
        }

        obj = obj_map.get(media_type)
        if obj is None:
            return None

        value = getattr(obj, field_name, None)

        # Handle null sorting - nulls should go last (or first for last_watched ascending)
        if value is None:
            if field_name == "last_watched" and direction == "ascending":
                # Return a very old date for nulls first
                return datetime.min
            # Return a very large value for nulls last in ascending, very small for descending
            if direction == "ascending":
                return float("inf")
            return float("-inf")

        return value

    def _get_show_episodes_sort_value(
        self,
        show: Show,
        category: str,
        field_name: str,
    ) -> Any:
        """Get aggregated value for show-episodes sorting."""
        if field_name == "last_watched":
            watch_date = self._show_last_watched.get(show.id)
            if watch_date is None:
                return datetime.min
            return watch_date

        if field_name == "random":
            # Use show ID + effective seed for consistent randomization per show
            seed_str = f"{show.id!s}:{self._effective_seed}"
            random.seed(seed_str)
            value = random.random()
            random.seed()  # Reset seed
            return value

        # Get all episodes for this show
        show_episodes = self._session.exec(
            select(Episode)
            .join(Season, Episode.season_id == Season.id)
            .where(
                and_(
                    Season.show_id == show.id,
                    col(Episode.deleted_at).is_(None),
                ),
            ),
        ).all()

        if not show_episodes:
            return 0

        values = [getattr(ep, field_name, None) for ep in show_episodes]
        values = [v for v in values if v is not None]

        if not values:
            return 0

        match category:
            case "sum":
                return sum(values)
            case "avg":
                return sum(values) / len(values)
            case "count":
                return len(values)
            case "max":
                return max(values)
            case "min":
                return min(values)
            case "first_value":
                return values[0] if values else 0
            case _:
                return 0

    def _show_recently_aired(self, show: Show, days: int) -> int:
        """Check if show has episodes that aired recently."""
        recent_date = tz_datetime.now() - timedelta(days=days)
        recent_episode = self._session.exec(
            select(Episode.id)
            .join(Season, Episode.season_id == Season.id)
            .where(
                and_(
                    Season.show_id == show.id,
                    col(Episode.air_date).is_not(None),
                    Episode.air_date >= recent_date,
                    col(Episode.deleted_at).is_(None),
                ),
            )
            .limit(1),
        ).first()

        return 1 if recent_episode else 0

    def _randomly_interleave_episodes(self, episodes: list[Episode]) -> list[Episode]:
        """Randomly interleave episodes by show."""
        show_episodes: dict[UUID, list[Episode]] = defaultdict(list)
        for episode in episodes:
            show_id = episode.season.show_id
            show_episodes[show_id].append(episode)

        output: list[Episode] = []
        show_lists = list(show_episodes.values())

        rng = random.Random(self._effective_seed)  # noqa: S311
        while show_lists:
            chosen_list = rng.choice(show_lists)
            output.append(chosen_list.pop(0))

            if not chosen_list:
                show_lists.remove(chosen_list)

        return output

    def _interleave_by_last_sort_value_python(
        self,
        results: list[tuple[Episode, Season, Show, ChannelShow]],
    ) -> list[Episode]:
        """Interleave episodes based on the last sort value."""
        if not self._media_filter.sort_by:
            return [ep for ep, _, _, _ in results]

        last_sort_key = self._media_filter.sort_by[-1]

        # Group episodes by the last sort value
        sort_value_groups: dict[str, list[Episode]] = defaultdict(list)
        for item in results:
            episode = item[0]
            sort_value = self._get_sort_value(item, last_sort_key)
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
            .join(Season, Episode.season_id == Season.id)
            .join(Show, Season.show_id == Show.id)
            .join(ChannelShow, ChannelShow.show_id == Show.id)
            .where(col(Episode.id).in_([ep.id for ep in episodes]))
            .where(col(ChannelShow.channel_id).in_(self._channel_ids))
        )

        results = self._session.exec(query).all()

        # Apply whitelist filtering
        episode_channels: dict[UUID, UUID] = {}
        for episode_id, channel_id in results:
            episode = next((ep for ep in episodes if ep.id == episode_id), None)
            if not episode:
                continue

            season = episode.season
            show = season.show

            # Get channel_show
            channel_show = self._session.exec(
                select(ChannelShow).where(
                    and_(
                        ChannelShow.show_id == show.id,
                        ChannelShow.channel_id == channel_id,
                    ),
                ),
            ).first()

            if not channel_show:
                continue

            if self._check_whitelist(episode, season, channel_show):
                episode_channels[episode_id] = channel_id

        return episode_channels

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
        ):
            return True

        model_map: dict[str, type[Episode | Season | Show | Source]] = {
            "episode": Episode,
            "season": Season,
            "show": Show,
            "source": Source,
        }

        model = model_map.get(media_type)
        if model is None:
            return False

        return field_name in model.model_fields
