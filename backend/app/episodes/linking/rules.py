# TODO: Validate

from collections.abc import Callable, Collection, Hashable, Iterable

from app.episodes.models import Episode
from app.episodes.name_matching import loose_plaintext, plaintext


# TODO: Validate
def episode_name(episode: Episode) -> str | None:
    return episode.name


# TODO: Validate
def plaintext_name(episode: Episode) -> str:
    return plaintext(episode.name)


# TODO: Validate
def loose_name(episode: Episode) -> str:
    return loose_plaintext(episode.name)


# TODO: Validate
def plaintext_description(episode: Episode) -> str:
    return plaintext(episode.description)


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
    def keys_of(episode: Episode) -> Iterable[Hashable | None]:
        return (key_of(episode),)

    return keys_of


# TODO: Validate
def name_key(
    name_of: Callable[[Episode], str | None],
) -> Callable[[Episode], Hashable | None]:
    def key_of(episode: Episode) -> Hashable | None:
        return name_of(episode) or None

    return key_of


# TODO: Validate
def name_and_episode_index_key(
    name_of: Callable[[Episode], str | None],
) -> Callable[[Episode], Hashable | None]:
    def key_of(episode: Episode) -> Hashable | None:
        name = name_of(episode)
        if not name:
            return None
        return (name, episode.episode_number)

    return key_of


# TODO: Validate
def name_and_episode_indexes_keys(
    name_of: Callable[[Episode], str | None],
    numbers_of: Callable[[Episode], Collection[int]],
) -> Callable[[Episode], Iterable[Hashable | None]]:
    def keys_of(episode: Episode) -> Iterable[Hashable | None]:
        name = name_of(episode)
        if not name:
            return ()
        return [(name, number) for number in numbers_of(episode)]

    return keys_of


# TODO: Validate
def name_season_and_episode_number_key(
    name_of: Callable[[Episode], str | None],
    season_number_of: Callable[[Episode], int | None],
) -> Callable[[Episode], Hashable | None]:
    def key_of(episode: Episode) -> Hashable | None:
        name = name_of(episode)
        season_number = season_number_of(episode)
        if not name or season_number is None or episode.episode_number is None:
            return None
        return (name, season_number, episode.episode_number)

    return key_of


# TODO: Validate
def season_and_episode_number_key(
    season_number_of: Callable[[Episode], int | None],
) -> Callable[[Episode], Hashable | None]:
    def key_of(episode: Episode) -> Hashable | None:
        season_number = season_number_of(episode)
        if season_number is None or episode.episode_number is None:
            return None
        return (season_number, episode.episode_number)

    return key_of
