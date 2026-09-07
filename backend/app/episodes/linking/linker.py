# TODO: Validate

import uuid
from collections.abc import Callable, Collection, Hashable, Iterable, Sequence

import numpy  # noqa: ICN001 - Spelled out, as abbreviated names are not used here.
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, select

from app.canonical_media.tmdb import (
    is_tmdb_key,
)
from app.episodes.linking.rules import (
    season_and_episode_number_key,
    single,
    unambiguous_lookup,
)
from app.episodes.linking.tmdb_facts import TmdbEpisodeFacts
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.episodes.name_matching import (
    is_only_numbered_name,
    is_untitled_name,
    loose_plaintext,
    name_parts,
    plaintext,
)
from app.episodes.preload import preload_episodes
from app.episodes.service.numbering import absolute_numbers
from app.episodes.text_matching import TextMatcher
from app.titles.models import Title


# TODO: Validate
class EpisodeLinker:
    # TODO: Validate
    def __init__(self, session: Session, title: Title) -> None:
        self.session = session
        self.title = title
        preload_episodes(session, [title, *title.canonical_titles])
        episodes = [
            episode
            for season in title.active_children
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
            for canonical_title in title.canonical_titles
            for season in canonical_title.active_children
            for episode in season.active_children
            if is_tmdb_key(episode.key)
        ]
        self.season_numbers = {
            episode.id: season.season_number
            for parent in (title, *title.canonical_titles)
            for season in parent.active_children
            for episode in season.active_children
        }
        self.facts = TmdbEpisodeFacts(
            session,
            title.canonical_titles,
            self.canonical_episodes,
        )
        self.facts.preload()
        preload_episodes(session, [title, *title.canonical_titles])
        self.absolute_numbers: dict[uuid.UUID, int] = {}
        for parent in (title, *title.canonical_titles):
            self.absolute_numbers |= absolute_numbers(
                [
                    (episode.id, season.season_number, episode.episode_number)
                    for season in parent.active_children
                    for episode in season.active_children
                ],
            )
        self._load_existing_links(
            [*self.episodes, *self.unnamed_episodes, *self.canonical_episodes],
        )

    # TODO: Validate
    def _load_canonical_flags(self, episodes: Sequence[Episode]) -> None:
        expired = {
            episode.id: episode
            for episode in episodes
            if "is_canonical" in instance_state(episode).unloaded
        }
        if not expired:
            return
        rows = self.session.exec(
            select(Episode.id, Episode.is_canonical).where(
                col(Episode.id).in_(list(expired)),
            ),
        ).all()
        for episode_id, is_canonical in rows:
            set_committed_value(expired[episode_id], "is_canonical", is_canonical)

    # TODO: Validate
    def _load_existing_links(self, episodes: Sequence[Episode]) -> None:
        self._load_canonical_flags(episodes)
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
    def link_title(self) -> None:
        self.link_named_episodes(self.episodes)
        self.link_unnamed_episodes(self.unnamed_episodes)

    # TODO: Validate
    def link_named_episodes(self, episodes: list[Episode]) -> list[Episode]:
        return self._link_by_tests(
            self._link_by_single_test(
                self._unlinked(episodes),
                self._exact_test(self.facts.names_of, self._own_name, "Exact name"),
            ),
            [
                self._exact_test(
                    self._descriptions_of,
                    self._own_description,
                    "Exact description",
                ),
                *self._scored_tests(
                    self.facts.names_of,
                    self._own_name,
                    "name",
                    blended=(0.5, 0.1),
                    embedding=(0.6, 0.0),
                ),
                self._split_test("Split name"),
                *self._scored_tests(
                    self._descriptions_of,
                    self._own_description,
                    "description",
                    blended=(0.4, 0.05),
                    embedding=(0.5, 0.0),
                ),
            ],
        )

    # TODO: Validate
    def link_unnamed_episodes(self, episodes: list[Episode]) -> list[Episode]:
        numbered = self._by_season_and_episode_number("Automatic: Numbering match")
        return self._link_by_tests(
            numbered(self._unlinked(episodes)),
            [
                self._exact_test(
                    self._descriptions_of,
                    self._own_description,
                    "Exact description",
                ),
                *self._scored_tests(
                    self._descriptions_of,
                    self._own_description,
                    "description",
                    blended=(0.4, 0.05),
                    embedding=(0.5, 0.0),
                ),
            ],
        )

    # TODO: Validate
    def _exact_index(
        self,
        texts_of: Callable[[Episode], Collection[str]],
    ) -> dict[str, set[Episode]]:
        index: dict[str, set[Episode]] = {}
        for tmdb_episode in self.canonical_episodes:
            for candidate_text in texts_of(tmdb_episode):
                if key := plaintext(candidate_text):
                    index.setdefault(key, set()).add(tmdb_episode)
        return index

    # TODO: Validate
    @staticmethod
    def _sole_match(index: dict[str, set[Episode]], text: str | None) -> Episode | None:
        key = plaintext(text)
        if not key:
            return None
        found = index.get(key, set())
        return next(iter(found)) if len(found) == 1 else None

    # TODO: Validate
    def _loose_index(
        self,
        texts_of: Callable[[Episode], Collection[str]],
    ) -> dict[str, set[Episode]]:
        index: dict[str, set[Episode]] = {}
        for tmdb_episode in self.canonical_episodes:
            for candidate_text in texts_of(tmdb_episode):
                if key := loose_plaintext(candidate_text):
                    index.setdefault(key, set()).add(tmdb_episode)
        return index

    # TODO: Validate
    @staticmethod
    def _contained_match(
        index: dict[str, set[Episode]],
        text: str | None,
    ) -> Episode | None:
        key = loose_plaintext(text)
        if not key:
            return None
        found = {
            tmdb_episode
            for candidate_key, tmdb_episodes in index.items()
            if candidate_key in key
            for tmdb_episode in tmdb_episodes
        }
        return next(iter(found)) if len(found) == 1 else None

    # TODO: Validate
    @staticmethod
    def _batched(
        test: Callable[[Episode], list[tuple[float, Episode]]],
    ) -> Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]:
        # TODO: Validate
        def batched(
            episodes: Sequence[Episode],
        ) -> list[list[tuple[float, Episode]]]:
            return [test(episode) for episode in episodes]

        return batched

    # TODO: Validate
    def _split_test(
        self,
        label: str,
    ) -> tuple[str, Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]]:
        index = self._exact_index(self.facts.names_of)
        loose_index = self._loose_index(self.facts.names_of)

        # TODO: Validate
        def test(episode: Episode) -> list[tuple[float, Episode]]:
            parts = name_parts(episode.name)[1:]
            if not parts:
                return []
            matched: list[Episode] = []
            for part in parts:
                found = self._sole_match(index, part) or self._contained_match(
                    loose_index,
                    part,
                )
                if found is None or found in matched:
                    return []
                matched.append(found)
            return [(1.0, tmdb_episode) for tmdb_episode in matched]

        return (label, self._batched(test))

    # TODO: Validate
    def _exact_test(
        self,
        texts_of: Callable[[Episode], Collection[str]],
        own_text_of: Callable[[Episode], str | None],
        label: str,
    ) -> tuple[str, Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]]:
        index = self._exact_index(texts_of)

        # TODO: Validate
        def test(episode: Episode) -> list[tuple[float, Episode]]:
            found = self._sole_match(index, own_text_of(episode))
            return [(1.0, found)] if found else []

        return (label, self._batched(test))

    # TODO: Validate
    def _link_by_single_test(
        self,
        episodes: list[Episode],
        test: tuple[
            str,
            Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]],
        ],
    ) -> list[Episode]:
        label, run = test
        for start in range(0, len(episodes), 256):
            batch = episodes[start : start + 256]
            for episode, found in zip(batch, run(batch), strict=True):
                for score, tmdb_episode in found:
                    self._claim(
                        episode,
                        tmdb_episode,
                        f"Automatic: {label} match ({round(score * 100)}%)",
                    )
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_by_tests(
        self,
        episodes: list[Episode],
        tests: list[
            tuple[str, Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]]
        ],
    ) -> list[Episode]:
        for start in range(0, len(episodes), 256):
            batch = episodes[start : start + 256]
            found_by_test = [(label, test(batch)) for label, test in tests]
            for position, episode in enumerate(batch):
                self._link_one_by_tests(
                    episode,
                    [
                        (label, found[position])
                        for label, found in found_by_test
                        if found[position]
                    ],
                )
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_one_by_tests(
        self,
        episode: Episode,
        results: list[tuple[str, list[tuple[float, Episode]]]],
    ) -> None:
        if not results:
            return

        matched = {
            frozenset(tmdb_episode.id for _score, tmdb_episode in found)
            for _label, found in results
        }
        widest = max(matched, key=len)
        if any(not found <= widest for found in matched):
            return

        results = [
            (label, found)
            for label, found in results
            if frozenset(tmdb_episode.id for _score, tmdb_episode in found) == widest
        ]
        labels = ", ".join(label for label, _found in results)
        for score, tmdb_episode in results[0][1]:
            self._claim(
                episode,
                tmdb_episode,
                f"Automatic: {labels} match ({round(score * 100)}%)",
            )

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
            note=note,
        )
        link.episode = episode
        link.canonical_episode = tmdb_episode
        episode.canonical_episode_links.append(link)
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
    def _absolute_number_of(self, episode: Episode) -> int | None:
        return self.absolute_numbers.get(episode.id)

    # TODO: Validate
    def _numbering_agrees(self, episode: Episode, tmdb_episode: Episode) -> bool:
        season_number = self._season_number_of(episode)
        if (
            season_number is not None
            and episode.episode_number is not None
            and season_number == self._season_number_of(tmdb_episode)
            and episode.episode_number == tmdb_episode.episode_number
        ):
            return True
        canonical_absolute = self._absolute_number_of(tmdb_episode)
        if canonical_absolute is not None and (
            episode.episode_number == canonical_absolute
        ):
            return True
        absolute_number = self._absolute_number_of(episode)
        if absolute_number is None:
            return False
        return (
            absolute_number == canonical_absolute
            or absolute_number in self.facts.alternate_numbers_of(tmdb_episode)
        )

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
        if not self._numbering_agrees(episode, tmdb_episode):
            return None
        return ranked[0]

    # TODO: Validate
    @staticmethod
    def _candidates_of(
        entries: list[tuple[Episode, str]],
    ) -> tuple[list[Episode], numpy.ndarray]:
        candidates: list[Episode] = []
        positions: dict[uuid.UUID, int] = {}
        entry_candidates: list[int] = []
        for tmdb_episode, _text in entries:
            position = positions.get(tmdb_episode.id)
            if position is None:
                position = len(candidates)
                positions[tmdb_episode.id] = position
                candidates.append(tmdb_episode)
            entry_candidates.append(position)
        return candidates, numpy.asarray(entry_candidates, dtype=numpy.intp)

    # TODO: Validate
    @staticmethod
    def _runner_up(best: numpy.ndarray, first: int) -> int | None:
        before = best[:first]
        after = best[first + 1 :]
        if not before.size and not after.size:
            return None
        if not after.size or (before.size and before.max() >= after.max()):
            return int(numpy.argmax(before))
        return first + 1 + int(numpy.argmax(after))

    # TODO: Validate
    @staticmethod
    def _ranked(
        candidates: list[Episode],
        entry_candidates: numpy.ndarray,
        scores: numpy.ndarray,
    ) -> list[tuple[float, Episode]]:
        best: numpy.ndarray
        if len(candidates) == len(scores):
            best = scores
        else:
            best = numpy.full(len(candidates), -1.0)
            numpy.maximum.at(best, entry_candidates, scores)
        if not best.size:
            return []

        first = int(numpy.argmax(best))
        if best[first] <= -1.0:
            return []
        ranked = [(float(best[first]), candidates[first])]

        second = EpisodeLinker._runner_up(best, first)
        if second is not None and best[second] > -1.0:
            ranked.append((float(best[second]), candidates[second]))
        return ranked

    # TODO: Validate
    def _scored_tests(
        self,
        texts_of: Callable[[Episode], Collection[str]],
        own_text_of: Callable[[Episode], str | None],
        label: str,
        *,
        blended: tuple[float, float],
        embedding: tuple[float, float],
    ) -> list[
        tuple[str, Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]]
    ]:
        entries = [
            (tmdb_episode, text)
            for tmdb_episode in self.canonical_episodes
            for text in texts_of(tmdb_episode)
        ]
        if not entries:
            return []
        matcher = TextMatcher([text for _tmdb_episode, text in entries])
        candidates, entry_candidates = self._candidates_of(entries)

        # TODO: Validate
        def scored(
            scores_of: Callable[[list[str]], numpy.ndarray],
            floor: float,
            margin: float,
        ) -> Callable[[Sequence[Episode]], list[list[tuple[float, Episode]]]]:
            # TODO: Validate
            def test(
                episodes: Sequence[Episode],
            ) -> list[list[tuple[float, Episode]]]:
                own_texts = [
                    (own_text_of(episode) or "").strip() for episode in episodes
                ]
                if not own_texts:
                    return []
                score_rows = scores_of(own_texts)
                results: list[list[tuple[float, Episode]]] = []
                for episode, own_text, scores in zip(
                    episodes,
                    own_texts,
                    score_rows,
                    strict=True,
                ):
                    found = (
                        self._confident_match(
                            episode,
                            self._ranked(candidates, entry_candidates, scores),
                            floor,
                            margin,
                        )
                        if own_text
                        else None
                    )
                    results.append([found] if found else [])
                return results

            return test

        return [
            (f"Blended {label}", scored(matcher.blended_scores_of, *blended)),
            (f"Embedding {label}", scored(matcher.embedding_scores_of, *embedding)),
        ]
