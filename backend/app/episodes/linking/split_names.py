# TODO: Validate

import uuid
from collections.abc import Callable, Sequence

from app.episodes.linking.rules import (
    loose_name,
    name_key,
    plaintext_name,
    single,
    unambiguous_lookup,
)
from app.episodes.models import Episode
from app.media.name_matching import (
    contains_name,
    loose_plaintext,
    name_parts,
    plaintext,
)

CONTAINED_NAME_NOTE = "Automatic: Contained name match"


# TODO: Validate
class SplitNameLinker:
    # TODO: Validate
    def __init__(
        self,
        canonical_episodes: Sequence[Episode],
        episodes: Sequence[Episode],
        claim_once: Callable[[Episode, Episode, str], None],
    ) -> None:
        self.canonical_episodes = canonical_episodes
        self.episodes = episodes
        self.claim_once = claim_once
        self.parts_by_episode = {
            episode.id: name_parts(episode.name) for episode in episodes
        }
        self.tmdb_names = {
            tmdb_episode.id: plaintext(tmdb_episode.name)
            for tmdb_episode in canonical_episodes
        }
        self.settled: set[tuple[uuid.UUID, str]] = set()
        self.holders: dict[uuid.UUID, dict[uuid.UUID, tuple[Episode, str]]] = {}
        self.holding: dict[tuple[uuid.UUID, str], list[Episode]] = {}

    # TODO: Validate
    def link(self) -> None:
        self._link_exact_parts()
        self._find_contained_parts()
        self._link_held_names()
        self._link_holding_names()

    # TODO: Validate
    def _unsettled_parts(self, episode: Episode) -> list[str]:
        return [
            part
            for part in self.parts_by_episode[episode.id]
            if (episode.id, part) not in self.settled
        ]

    # TODO: Validate
    def _link_exact_parts(self) -> None:
        for name_of, form, note in (
            (plaintext_name, plaintext, "Automatic: Split name match"),
            (loose_name, loose_plaintext, "Automatic: Loose split name match"),
        ):
            by_name = unambiguous_lookup(
                self.canonical_episodes,
                single(name_key(name_of)),
            )
            for episode in self.episodes:
                for part in self._unsettled_parts(episode):
                    if match := by_name.get(form(part)):
                        self.claim_once(episode, match, note)
                        self.settled.add((episode.id, part))

    # TODO: Validate
    def _find_contained_parts(self) -> None:
        for episode in self.episodes:
            for part in self._unsettled_parts(episode):
                plain_part = plaintext(part)
                for tmdb_episode in self.canonical_episodes:
                    tmdb_name = self.tmdb_names[tmdb_episode.id]
                    if contains_name(plain_part, tmdb_name):
                        self.holders.setdefault(tmdb_episode.id, {}).setdefault(
                            episode.id,
                            (episode, part),
                        )
                    elif contains_name(tmdb_name, plain_part):
                        self.holding.setdefault((episode.id, part), []).append(
                            tmdb_episode,
                        )

    # TODO: Validate
    def _link_held_names(self) -> None:
        for tmdb_episode in self.canonical_episodes:
            holding_episodes = self.holders.get(tmdb_episode.id, {})
            if len(holding_episodes) != 1:
                continue
            episode, part = next(iter(holding_episodes.values()))
            self.claim_once(episode, tmdb_episode, CONTAINED_NAME_NOTE)
            self.settled.add((episode.id, part))

    # TODO: Validate
    def _link_holding_names(self) -> None:
        for episode in self.episodes:
            for part in self._unsettled_parts(episode):
                matches = self.holding.get((episode.id, part), [])
                if len(matches) != 1:
                    continue
                self.claim_once(episode, matches[0], CONTAINED_NAME_NOTE)
                self.settled.add((episode.id, part))
