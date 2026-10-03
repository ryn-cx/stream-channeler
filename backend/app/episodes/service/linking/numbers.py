# TODO: Validate
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from app.episodes.service.linking.details import EpisodeDetails
from app.episodes.service.names.forms import strip_show_and_season
from app.episodes.service.names.matching import (
    is_only_numbered_name,
    is_untitled_name,
)
from app.episodes.service.numbering import absolute_numbers

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


# TODO: Validate
def season_and_episode_number(episode: EpisodeDetails) -> tuple[int, ...] | None:
    """Return the episode's season and episode number, or nothing when either one is
    missing.
    """
    if episode.season_number is None or episode.episode_number is None:
        return None
    return (episode.season_number, episode.episode_number)


# TODO: Validate
def season_episode_name_tuple(
    episode: EpisodeDetails,
) -> tuple[int | None, int, str] | None:
    # Not sure if there will ever be episode 0 but might as well support it.
    if episode.episode_number is None or not episode.normalized_name:
        return None
    return (episode.season_number, episode.episode_number, episode.normalized_name)


# TODO: Validate
def absolute_episode_number(episode: EpisodeDetails) -> tuple[int, ...] | None:
    """Return how far into the title the episode is, or nothing when that is not known."""
    if episode.absolute_number is None:
        return None
    return (episode.absolute_number,)


# TODO: Validate
def episode_number(episode: EpisodeDetails) -> tuple[int, ...] | None:
    if episode.episode_number is None or episode.season_number == 0:
        return None
    return (episode.episode_number,)


# TODO: Validate
def meaningless_name(episode: EpisodeDetails) -> bool:
    """Say whether the episode's name says nothing about which episode it is, either
    because there is no name, or because it is only a placeholder like Untitled or
    Episode 1.
    """
    name = episode.normalized_name
    return not name or is_untitled_name(name) or is_only_numbered_name(name)


# TODO: Validate
def stripped_name(episode: EpisodeDetails) -> str:
    return strip_show_and_season(
        episode.name,
        episode.title_name,
        episode.season_name,
        episode.season_number,
    )


# TODO: Validate
def has_no_name(
    episode: EpisodeDetails,
    *,
    every_stripped_name_is_empty: bool,
) -> bool:
    if not episode.name or not episode.name.strip():
        return True
    name = stripped_name(episode)
    if not name:
        return every_stripped_name_is_empty
    return name.isdigit() or is_untitled_name(name) or is_only_numbered_name(name)


# TODO: Validate
def same_number(episode: EpisodeDetails, tmdb_episode: EpisodeDetails) -> bool:
    """Say whether the two episodes are numbered the same, either by season and episode
    number, by absolute number, or by the site's straight-through number against
    TMDB's absolute number.
    """
    numbered = season_and_episode_number(episode)
    if numbered is not None and numbered == season_and_episode_number(tmdb_episode):
        return True
    absolute = absolute_episode_number(episode)
    if absolute is not None and absolute == absolute_episode_number(tmdb_episode):
        return True
    straight_through = episode_number(episode)
    return straight_through is not None and straight_through == absolute_episode_number(
        tmdb_episode,
    )


# TODO: Validate
def set_absolute_numbers(episodes: Sequence[EpisodeDetails]) -> None:
    """Work out how far into the title each episode is and store it on the record."""
    numbers = absolute_numbers(
        [
            (episode.id, episode.season_number, episode.episode_number)
            for episode in episodes
        ],
    )
    for episode in episodes:
        episode.absolute_number = numbers.get(episode.id)


# TODO: Validate
def number_to_episodes[DetailsT: EpisodeDetails](
    episodes: Sequence[DetailsT],
    number_of: Callable[[DetailsT], tuple[int, ...] | None],
) -> defaultdict[tuple[int, ...], list[DetailsT]]:
    grouped: defaultdict[tuple[int, ...], list[DetailsT]] = defaultdict(list)
    for episode in episodes:
        number = number_of(episode)
        if number is not None:
            grouped[number].append(episode)
    return grouped
