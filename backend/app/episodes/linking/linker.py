# TODO: Validate

from collections.abc import Callable, Collection, Hashable, Iterable, Sequence
from itertools import pairwise

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, select

from app.canonical_media.keys import is_tmdb_key
from app.episodes.linking.rules import (
    season_and_episode_number_key,
    single,
    unambiguous_lookup,
)
from app.episodes.linking.tmdb_facts import TmdbEpisodeFacts
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.episodes.name_matching import (
    contains_name,
    is_only_numbered_name,
    is_untitled_name,
    plaintext,
)
from app.episodes.preload import preload_episodes
from app.episodes.text_matching import TextMatcher
from app.shows.models import Show


# TODO: Validate
class EpisodeLinker:
    # TODO: Validate
    def __init__(self, session: Session, show: Show) -> None:
        self.session = session
        self.show = show
        preload_episodes(session, [show, *show.canonical_shows])
        episodes = [
            episode
            for season in show.active_children
            for episode in season.active_children
        ]
        self.episodes = [
            episode for episode in episodes if not self._has_blacklisted_name(episode)
        ]
        self.unnamed_episodes = [
            episode for episode in episodes if self._has_blacklisted_name(episode)
        ]
        self.canonical_episodes = [
            episode
            for canonical_show in show.canonical_shows
            for season in canonical_show.active_children
            for episode in season.active_children
            if is_tmdb_key(episode.key)
        ]
        self.season_numbers = {
            episode.id: season.season_number
            for parent in (show, *show.canonical_shows)
            for season in parent.active_children
            for episode in season.active_children
        }
        self._load_existing_links(
            [*self.episodes, *self.unnamed_episodes, *self.canonical_episodes],
        )
        self.facts = TmdbEpisodeFacts(
            session,
            show.canonical_shows,
            self.canonical_episodes,
        )

    # TODO: Validate
    def _load_existing_links(self, episodes: Sequence[Episode]) -> None:
        unread = [
            episode
            for episode in episodes
            if "canonical_episode_links" in instance_state(episode).unloaded
        ]
        for episode in unread:
            if episode.is_canonical:
                set_committed_value(episode, "canonical_episode_links", [])

        linked = [episode.id for episode in unread if not episode.is_canonical]
        if not linked:
            return
        self.session.exec(
            select(Episode)
            .where(col(Episode.id).in_(linked))
            .options(
                selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                    EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
                ),
            ),
        ).all()

    # TODO: Validate
    def link_show(self) -> None:
        self.link_named_episodes(self.episodes)
        self.link_unnamed_episodes(self.unnamed_episodes)

    # TODO: Validate
    def link_named_episodes(self, episodes: list[Episode]) -> list[Episode]:
        return self._link_by_tests(
            self._unlinked(episodes),
            [
                *self._scored_tests(
                    self.facts.names_of,
                    self._own_name,
                    "name",
                    blended=(0.5, 0.1),
                    embedding=(0.6, 0.1),
                ),
                self._contained_test("Contained name"),
                *self._scored_tests(
                    self._descriptions_of,
                    self._own_description,
                    "description",
                    blended=(0.4, 0.15),
                    embedding=(0.5, 0.15),
                ),
            ],
        )

    # TODO: Validate
    def link_unnamed_episodes(self, episodes: list[Episode]) -> list[Episode]:
        numbered = self._by_season_and_episode_number("Automatic: Numbering match")
        return self._link_by_tests(
            numbered(self._unlinked(episodes)),
            self._scored_tests(
                self._descriptions_of,
                self._own_description,
                "description",
                blended=(0.4, 0.15),
                embedding=(0.5, 0.15),
            ),
        )

    # TODO: Validate
    def _link_by_tests(
        self,
        episodes: list[Episode],
        tests: list[tuple[str, Callable[[Episode], list[tuple[float, Episode]]]]],
    ) -> list[Episode]:
        for episode in episodes:
            results = [
                (label, found) for label, test in tests if (found := test(episode))
            ]
            if not results:
                continue

            matched = {
                frozenset(tmdb_episode.id for _score, tmdb_episode in found)
                for _label, found in results
            }
            if len(matched) != 1:
                continue

            labels = ", ".join(label for label, _found in results)
            for score, tmdb_episode in results[0][1]:
                self._claim(
                    episode,
                    tmdb_episode,
                    f"Automatic: {labels} match ({round(score * 100)}%)",
                )
        return self._unlinked(episodes)

    # TODO: Validate
    @staticmethod
    def _own_name(episode: Episode) -> str | None:
        return episode.name

    # TODO: Validate
    @staticmethod
    def _own_description(episode: Episode) -> str | None:
        return episode.description

    # TODO: Validate
    @staticmethod
    def _descriptions_of(tmdb_episode: Episode) -> tuple[str, ...]:
        description = (tmdb_episode.description or "").strip()
        return (description,) if description else ()

    # TODO: Validate
    @staticmethod
    def _run(
        steps: Sequence[Callable[[list[Episode]], list[Episode]]],
        episodes: list[Episode],
    ) -> list[Episode]:
        for step in steps:
            if not episodes:
                break
            episodes = step(episodes)
        return episodes

    # TODO: Validate
    @staticmethod
    def _has_blacklisted_name(episode: Episode) -> bool:
        name = episode.name
        if not name:
            return True
        return is_only_numbered_name(name) or is_untitled_name(name)

    # TODO: Validate
    def _season_number_of(self, episode: Episode) -> int | None:
        return self.season_numbers.get(episode.id)

    # TODO: Validate
    @staticmethod
    def _unlinked(episodes: list[Episode]) -> list[Episode]:
        return [episode for episode in episodes if not episode.canonical_episode_links]

    # TODO: Validate
    def _claim(self, episode: Episode, tmdb_episode: Episode, note: str) -> None:
        link = EpisodeCanonicalEpisode(
            episode_id=episode.id,
            canonical_episode_id=tmdb_episode.id,
            sort_order=episode.sort_order,
        )
        link.episode = episode
        link.canonical_episode = tmdb_episode
        episode.canonical_episode_links.append(link)
        episode.canonical_episode_note = note
        self.session.add(link)

    # TODO: Validate
    def _by_key(
        self,
        keys_of: Callable[[Episode], Iterable[Hashable | None]],
        key_of: Callable[[Episode], Hashable | None],
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        # TODO: Validate
        def step(episodes: list[Episode]) -> list[Episode]:
            index = unambiguous_lookup(self.canonical_episodes, keys_of)
            for episode in episodes:
                key = key_of(episode)
                if key is None:
                    continue
                if match := index.get(key):
                    self._claim(episode, match, note)
            return self._unlinked(episodes)

        return step

    # TODO: Validate
    def _by_season_and_episode_number(
        self,
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        key_of = season_and_episode_number_key(self._season_number_of)
        return self._by_key(single(key_of), key_of, note)

    # TODO: Validate
    def _orders_of(self, tmdb_episode: Episode) -> set[int]:
        orders = set(self.facts.alternate_numbers_of(tmdb_episode))
        if tmdb_episode.episode_number is not None:
            orders.add(tmdb_episode.episode_number)
        return orders

    # TODO: Validate
    def _confident_match(
        self,
        episode: Episode,
        ranked: list[tuple[float, Episode]],
        floor: float,
        margin: float,
    ) -> tuple[float, Episode] | None:
        if not ranked:
            return None

        score, tmdb_episode = ranked[0]
        if score < floor:
            return None
        if len(ranked) > 1 and score - ranked[1][0] < margin:
            return None
        if score >= 0.99:  # noqa: PLR2004 - Written the very same way on both sides.
            return ranked[0]
        if episode.episode_number is None or episode.episode_number not in (
            self._orders_of(tmdb_episode)
        ):
            return None
        return ranked[0]

    # TODO: Validate
    @staticmethod
    def _contained_spans(
        own_name: str,
        candidates: list[tuple[Episode, str]],
    ) -> dict[Episode, tuple[int, int]]:
        around: dict[Episode, list[tuple[int, int]]] = {}
        within: set[Episode] = set()
        for tmdb_episode, name in candidates:
            if contains_name(own_name, name):
                start = own_name.find(name)
                around.setdefault(tmdb_episode, []).append((start, start + len(name)))
            elif contains_name(name, own_name):
                within.add(tmdb_episode)

        spans = {
            tmdb_episode: max(found, key=lambda span: span[1] - span[0])
            for tmdb_episode, found in around.items()
        }
        for tmdb_episode in within:
            spans.setdefault(tmdb_episode, (0, len(own_name)))
        return spans

    # TODO: Validate
    @staticmethod
    def _spans_overlap(spans: Collection[tuple[int, int]]) -> bool:
        return any(later[0] < earlier[1] for earlier, later in pairwise(sorted(spans)))

    # TODO: Validate
    def _contained_test(
        self,
        label: str,
    ) -> tuple[str, Callable[[Episode], list[tuple[float, Episode]]]]:
        candidates = [
            (tmdb_episode, plaintext(name))
            for tmdb_episode in self.canonical_episodes
            for name in self.facts.names_of(tmdb_episode)
            if plaintext(name)
        ]

        # TODO: Validate
        def test(episode: Episode) -> list[tuple[float, Episode]]:
            own_name = plaintext(episode.name)
            if not own_name or not candidates:
                return []
            spans = self._contained_spans(own_name, candidates)
            if not spans or self._spans_overlap(spans.values()):
                return []
            return [(1.0, tmdb_episode) for tmdb_episode in spans]

        return (label, test)

    # TODO: Validate
    @staticmethod
    def _ranked(
        entries: list[tuple[Episode, str]],
        scores: list[float],
    ) -> list[tuple[float, Episode]]:
        best: dict[Episode, float] = {}
        for (tmdb_episode, _text), score in zip(entries, scores, strict=True):
            if score > best.get(tmdb_episode, -1.0):
                best[tmdb_episode] = score
        return sorted(
            ((score, tmdb_episode) for tmdb_episode, score in best.items()),
            key=lambda scoring: scoring[0],
            reverse=True,
        )

    # TODO: Validate
    def _scored_tests(
        self,
        texts_of: Callable[[Episode], Collection[str]],
        own_text_of: Callable[[Episode], str | None],
        label: str,
        *,
        blended: tuple[float, float],
        embedding: tuple[float, float],
    ) -> list[tuple[str, Callable[[Episode], list[tuple[float, Episode]]]]]:
        entries = [
            (tmdb_episode, text)
            for tmdb_episode in self.canonical_episodes
            for text in texts_of(tmdb_episode)
        ]
        if not entries:
            return []
        matcher = TextMatcher([text for _tmdb_episode, text in entries])

        # TODO: Validate
        def scored(
            scores_of: Callable[[str], list[float]],
            floor: float,
            margin: float,
        ) -> Callable[[Episode], list[tuple[float, Episode]]]:
            # TODO: Validate
            def test(episode: Episode) -> list[tuple[float, Episode]]:
                own_text = (own_text_of(episode) or "").strip()
                if not own_text:
                    return []
                found = self._confident_match(
                    episode,
                    self._ranked(entries, scores_of(own_text)),
                    floor,
                    margin,
                )
                return [found] if found else []

            return test

        return [
            (f"Blended {label}", scored(matcher.blended_scores, *blended)),
            (f"Embedding {label}", scored(matcher.embedding_scores, *embedding)),
        ]
