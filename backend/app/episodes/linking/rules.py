# TODO: Validate

from collections.abc import Callable, Collection, Hashable, Iterable

from app.episodes.models import Episode


# TODO: Validate
def unambiguous_lookup(
    episodes: Collection[Episode],
    keys_of: Callable[[Episode], Iterable[Hashable | None]],
) -> dict[Hashable, Episode]:
    candidates: dict[Hashable, Episode] = {}
    ambiguous: set[Hashable] = set()
    for episode in episodes:
        for key in keys_of(episode):
            if key is None:
                continue
            if key in candidates:
                ambiguous.add(key)
                continue
            candidates[key] = episode
    for key in ambiguous:
        del candidates[key]
    return candidates


# TODO: Validate
def single(
    key_of: Callable[[Episode], Hashable | None],
) -> Callable[[Episode], Iterable[Hashable | None]]:
    # TODO: Validate
    def keys_of(episode: Episode) -> Iterable[Hashable | None]:
        return (key_of(episode),)

    return keys_of


# TODO: Validate
def season_and_episode_number_key(
    season_number_of: Callable[[Episode], int | None],
) -> Callable[[Episode], Hashable | None]:
    # TODO: Validate
    def key_of(episode: Episode) -> Hashable | None:
        season_number = season_number_of(episode)
        if season_number is None or episode.episode_number is None:
            return None
        return (season_number, episode.episode_number)

    return key_of
