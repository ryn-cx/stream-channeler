# TODO: Validate

import uuid
from collections.abc import Callable, Collection, Hashable, Iterable, Sequence

from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, select

from app.canonical_media.keys import is_tmdb_key
from app.episodes.linking.rules import (
    episode_name,
    loose_name,
    name_and_episode_index_key,
    name_and_episode_indexes_keys,
    name_key,
    name_season_and_episode_number_key,
    plaintext_description,
    plaintext_name,
    season_and_episode_number_key,
    single,
    unambiguous_lookup,
)
from app.episodes.linking.split_names import SplitNameLinker
from app.episodes.linking.tmdb_facts import TmdbEpisodeFacts
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.episodes.name_forms import plaintext_forms
from app.episodes.name_matching import (
    is_only_numbered_name,
    is_untitled_name,
    name_parts,
)
from app.episodes.preload import preload_episodes
from app.media.media_type import MediaType
from app.seasons.models import Season
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
        named = episodes
        own_numbers: Callable[[Episode], Collection[int]] = Episode.own_episode_numbers
        alternate_numbers = self.facts.alternate_numbers_of
        episodes = self._run(
            (
                self._link_movie,
                self._by_name_season_and_episode_number(
                    episode_name,
                    "Automatic: Name and full numbering match",
                ),
                self._by_name_season_and_episode_number(
                    plaintext_name,
                    "Automatic: Plaintext name and full numbering match",
                ),
                self._by_name_and_episode_index(
                    episode_name,
                    own_numbers,
                    "Automatic: Name and number match",
                ),
                self._by_name_and_episode_index(
                    plaintext_name,
                    own_numbers,
                    "Automatic: Plaintext name and number match",
                ),
                self._by_name_and_episode_index(
                    plaintext_description,
                    own_numbers,
                    "Automatic: Description and number match",
                ),
                self._by_name_and_episode_index(
                    episode_name,
                    alternate_numbers,
                    "Automatic: Name and alternate order number match",
                ),
                self._by_name_and_episode_index(
                    plaintext_name,
                    alternate_numbers,
                    "Automatic: Plaintext name and alternate order number match",
                ),
                self._by_similar_name_and_episode_index(
                    own_numbers,
                    "Automatic: Similar name and number match",
                ),
                self._by_similar_name_and_episode_index(
                    alternate_numbers,
                    "Automatic: Similar name and alternate order number match",
                ),
                self._by_name(episode_name, "Automatic: Name match"),
                self._by_name(plaintext_name, "Automatic: Plaintext name match"),
                self._by_name(loose_name, "Automatic: Loose name match"),
                self._by_name(plaintext_description, "Automatic: Description match"),
                self._link_translated_name,
            ),
            self._unlinked(episodes),
        )
        episodes = self._link_name_parts(self._with_split_names(episodes, named))
        episodes = self._by_best_name("Automatic: Best name match")(episodes)
        return self._by_untitled_season_and_episode_number(
            "Automatic: Untitled numbering match",
        )(episodes)

    # TODO: Validate
    def link_unnamed_episodes(self, episodes: list[Episode]) -> list[Episode]:
        return self._run(
            (
                self._link_movie,
                self._by_season_and_episode_number("Automatic: Numbering match"),
                self._by_name_and_episode_index(
                    plaintext_description,
                    Episode.own_episode_numbers,
                    "Automatic: Description and number match",
                ),
                self._by_name(plaintext_description, "Automatic: Description match"),
            ),
            self._unlinked(episodes),
        )

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
    def _claim_once(self, episode: Episode, tmdb_episode: Episode, note: str) -> None:
        already_linked = any(
            link.canonical_episode_id == tmdb_episode.id
            for link in episode.canonical_episode_links
        )
        if not already_linked:
            self._claim(episode, tmdb_episode, note)

    # TODO: Validate
    def _by_key(
        self,
        keys_of: Callable[[Episode], Iterable[Hashable | None]],
        key_of: Callable[[Episode], Hashable | None],
        note: str,
        canonical_episodes: Collection[Episode] | None = None,
    ) -> Callable[[list[Episode]], list[Episode]]:
        def step(episodes: list[Episode]) -> list[Episode]:
            index = unambiguous_lookup(
                self.canonical_episodes
                if canonical_episodes is None
                else canonical_episodes,
                keys_of,
            )
            for episode in episodes:
                key = key_of(episode)
                if key is None:
                    continue
                if match := index.get(key):
                    self._claim(episode, match, note)
            return self._unlinked(episodes)

        return step

    # TODO: Validate
    def _by_name(
        self,
        name_of: Callable[[Episode], str | None],
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        key_of = name_key(name_of)
        return self._by_key(single(key_of), key_of, note)

    # TODO: Validate
    def _by_name_season_and_episode_number(
        self,
        name_of: Callable[[Episode], str | None],
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        key_of = name_season_and_episode_number_key(name_of, self._season_number_of)
        return self._by_key(single(key_of), key_of, note)

    # TODO: Validate
    def _by_season_and_episode_number(
        self,
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        key_of = season_and_episode_number_key(self._season_number_of)
        return self._by_key(single(key_of), key_of, note)

    # TODO: Validate
    def _by_untitled_season_and_episode_number(
        self,
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        key_of = season_and_episode_number_key(self._season_number_of)
        return self._by_key(
            single(key_of),
            key_of,
            note,
            [
                tmdb_episode
                for tmdb_episode in self.canonical_episodes
                if is_untitled_name(tmdb_episode.name)
            ],
        )

    # TODO: Validate
    def _by_name_and_episode_index(
        self,
        name_of: Callable[[Episode], str | None],
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        return self._by_key(
            name_and_episode_indexes_keys(name_of, numbers_of),
            name_and_episode_index_key(name_of),
            note,
        )

    # TODO: Validate
    def _link_movie(self, episodes: list[Episode]) -> list[Episode]:
        if (
            len(episodes) != 1
            or len(self.canonical_episodes) != 1
            or episodes[0].season.show.media_type is None
            or episodes[0].season.show.media_type.lower() != MediaType.movie
            or self.canonical_episodes[0].season.show.media_type != MediaType.movie
        ):
            return episodes

        episode = episodes[0]
        canonical_episode = self.canonical_episodes[0]
        if episode.canonical_episode_validated_at is None:
            self._claim(episode, canonical_episode, "Automatic: Movie match")
        return []

    # TODO: Validate
    def _link_translated_name(self, episodes: list[Episode]) -> list[Episode]:
        forms_by_tmdb_episode = self.facts.translated_name_forms
        for episode in episodes:
            if not (targets := plaintext_forms(episode.name)):
                continue

            matches = [
                tmdb_episode
                for tmdb_episode in self.canonical_episodes
                if forms_by_tmdb_episode.get(tmdb_episode.id, frozenset()) & targets
            ]
            if len(matches) != 1:
                continue
            self._claim(episode, matches[0], "Automatic: Translated name match")
        return self._unlinked(episodes)

    # TODO: Validate
    def _by_similar_name_and_episode_index(
        self,
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> Callable[[list[Episode]], list[Episode]]:
        def step(episodes: list[Episode]) -> list[Episode]:
            numbered_episodes = [
                episode for episode in episodes if episode.episode_number is not None
            ]
            if not numbered_episodes:
                return episodes

            named_canonical_episodes = unambiguous_lookup(
                self.canonical_episodes,
                single(name_key(plaintext_name)),
            )
            translated_episodes = {
                episode.id
                for episode in numbered_episodes
                if plaintext_name(episode) not in named_canonical_episodes
            }
            if translated_episodes:
                self.facts.preload_translations()

            for episode in numbered_episodes:
                score_of = (
                    self.facts.best_name_similarity
                    if episode.id in translated_episodes
                    else self.facts.raw_name_similarity
                )
                every_score = [
                    (score_of(episode, tmdb_episode), tmdb_episode)
                    for tmdb_episode in self.canonical_episodes
                ]
                scored = sorted(
                    (
                        (score, tmdb_episode)
                        for score, tmdb_episode in every_score
                        if episode.episode_number in numbers_of(tmdb_episode)
                    ),
                    key=lambda scoring: scoring[0],
                    reverse=True,
                )
                if not scored or scored[0][0] < 0.5:  # noqa: PLR2004
                    continue
                if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.1:  # noqa: PLR2004
                    continue
                if scored[0][0] < max(score for score, _episode in every_score):
                    continue

                self._claim(episode, scored[0][1], note)
            return self._unlinked(episodes)

        return step

    # TODO: Validate
    def _claimed_by_source(self) -> set[uuid.UUID]:
        statement = (
            select(col(EpisodeCanonicalEpisode.canonical_episode_id))
            .join(
                Episode,
                onclause=col(EpisodeCanonicalEpisode.episode_id) == Episode.id,
            )
            .join(Season, onclause=col(Episode.season_id) == Season.id)
            .join(Show, onclause=col(Season.show_id) == Show.id)
            .where(
                Show.source_id == self.show.source_id,
                col(Episode.deleted_at).is_(None),
            )
        )
        claimed = set(self.session.exec(statement).all())
        for episode in (*self.episodes, *self.unnamed_episodes):
            claimed.update(
                link.canonical_episode_id for link in episode.canonical_episode_links
            )
        return claimed

    # TODO: Validate
    def _by_best_name(self, note: str) -> Callable[[list[Episode]], list[Episode]]:
        def step(episodes: list[Episode]) -> list[Episode]:
            if not episodes:
                return episodes

            claimed = self._claimed_by_source()
            self.facts.preload_translations()
            for episode in episodes:
                scored = sorted(
                    (
                        (
                            self.facts.best_name_similarity(episode, tmdb_episode),
                            tmdb_episode,
                        )
                        for tmdb_episode in self.canonical_episodes
                        if tmdb_episode.id not in claimed
                    ),
                    key=lambda scoring: scoring[0],
                    reverse=True,
                )
                if not scored or scored[0][0] <= 0.8:  # noqa: PLR2004
                    continue
                self._claim(episode, scored[0][1], note)
                claimed.add(scored[0][1].id)
            return self._unlinked(episodes)

        return step

    # TODO: Validate
    @staticmethod
    def _with_split_names(
        episodes: list[Episode],
        named: list[Episode],
    ) -> list[Episode]:
        waiting = {episode.id for episode in episodes}
        return [
            *episodes,
            *(
                episode
                for episode in named
                if episode.id not in waiting and len(name_parts(episode.name)) > 1
            ),
        ]

    # TODO: Validate
    def _link_name_parts(self, episodes: list[Episode]) -> list[Episode]:
        SplitNameLinker(
            self.canonical_episodes,
            episodes,
            self._claim_once,
        ).link()
        return self._unlinked(episodes)
