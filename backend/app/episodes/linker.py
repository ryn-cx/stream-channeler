# TODO: Validate
"""Which TMDB episode each of a website's episodes is, and the writing of it down.

Every way an episode comes to stand for a TMDB record lives here: the matchers
`EpisodeLinker` reads in turn while a show is imported, and the by-hand settling
a `User` does from the matching screens. What reads those links back - the pages
of episodes still waiting on one, the choices offered for each - is the episode
service, which reads this module rather than holding any of it.
"""

import re
import uuid
from collections.abc import Callable, Collection, Sequence
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SHOW_LEVEL,
    is_tmdb_key,
    tmdb_id_of,
    tmdb_media_type_of,
)
from app.canonical_media.service import add_canonical_show
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeCanonicalEpisode,
)
from app.media.media_type import MediaType
from app.media.name_forms import plaintext_forms
from app.seasons.models import Season
from app.shows.models import Show

if TYPE_CHECKING:
    # Read only for what it names here. The plugin is built on the base every
    # plugin is, which reads this module in turn, so importing it outright is a
    # circle - which is why what reaches for it does so where it is used.
    from plugins.TMDB import TMDB


# The two themoviedb.org addresses that name one record. On TMDB's own links the
# title's name follows its id, which is no part of what the page names and is
# left where it lies.
_FILM_URL = re.compile(r"themoviedb\.org/movie/(?P<tmdb_id>\d+)")
_SERIES_EPISODE_URL = re.compile(
    r"themoviedb\.org/tv/(?P<tmdb_id>\d+)[^/]*"
    r"/season/(?P<season_number>\d+)/episode/(?P<episode_number>\d+)",
)


# TODO: Validate
# Held onto because a page of matches compares every episode against every
# candidate of its title, so the same handful of names are stripped down again
# for each pair - once per candidate per episode rather than once each.
@lru_cache(maxsize=16384)
def plaintext(name: str | None) -> str:
    if not name:
        return ""
    return "".join(
        character
        for character in _untitled_number(name).casefold()
        if character.isalnum()
    )


# A website that writes an episode's place into its name - "Session #11 Toys in
# the Attic", "Episode 3 - Gateway Shuffle" - has said the number twice and the
# title once, and the number is no part of what the episode is called. Read off
# both sides, since it is only ever on one of them and taking it off a name that
# never carried it changes nothing.
#
# A word and a number, or a number written as one, rather than a bare number: a
# title opening on a year or a count is a title and not a place in a run.
_NUMBERED_NAME = r"(?:(?:episode|ep|session|part)\s*\.?\s*#?\s*\d+|#\s*\d+)"
_NUMBERED_NAME_PREFIX = re.compile(
    rf"^\s*{_NUMBERED_NAME}\s*[-:.]?\s+",
    re.IGNORECASE,
)


# TODO: Validate
def _untitled_number(name: str) -> str:
    """Return `name` without the number a website wrote into the front of it.

    A name that is nothing but its number is left as it was: "Session #0" is what
    that episode is called, and taking the number out of it leaves nothing to
    match on at all.
    """
    untitled = _NUMBERED_NAME_PREFIX.sub("", name).strip()
    return untitled or name


# TODO: Validate
def similarity(name: str | None, other_name: str | None) -> float:
    stripped = plaintext(name)
    other_stripped = plaintext(other_name)
    if not stripped or not other_stripped:
        return 0.0
    # The same name written the same way is the answer without the comparing,
    # which is the case an exact match takes and the costliest one to work out.
    if stripped == other_stripped:
        return 1.0

    ratio = SequenceMatcher(None, stripped, other_stripped).ratio()
    if stripped not in other_stripped and other_stripped not in stripped:
        return ratio

    # One name sitting inside the other is worth only as much of the longer name
    # as it covers. A name of a letter or two is inside almost every other name,
    # and reading as a perfect match against the whole catalogue says nothing
    # about which episode it is. Never below what the names share outright, so
    # containment can only ever help.
    shorter, longer = sorted((stripped, other_stripped), key=len)
    return max(ratio, len(shorter) / len(longer))


# TODO: Validate
class EpisodeLinker:
    """Points a show's episodes at the canonical TMDB episodes they answer to.

    The matchers are read in turn, from the one that asks the most of a pair to
    the one that asks the least, and each is handed only what the one before it
    could not place. An episode that has been linked is dropped there and then,
    so the looser and costlier a matcher is the fewer episodes it has to read.

    Everything the matching is done by lives here rather than beside it in the
    module, so the whole of how an episode is paired with a TMDB record is read
    in one place. What the module keeps is what the matching screens read too -
    how alike two names are, how a title counts through its own run - which is
    no more the linker's than theirs.
    """

    # How alike two names have to read before the closer of them is taken as the
    # same episode, and how far ahead of the runner-up it has to be to be the one
    # answer.
    SIMILAR_NAME_FLOOR: ClassVar[float] = 0.5
    SIMILAR_NAME_LEAD: ClassVar[float] = 0.1

    # The names that are no name at all. A name that is the number and nothing
    # else - "Episode 5", "Ep. 5", "#5" - is where the episode is rather than
    # what it is called, and a website that names its episodes that way has said
    # nothing about them a name can be read against. Read once, when the episodes
    # are gathered, and the ones answering to it are matched on everything but
    # their names.
    NAME_BLACKLIST: ClassVar[tuple[re.Pattern[str], ...]] = (
        re.compile(rf"^\s*{_NUMBERED_NAME}\s*$", re.IGNORECASE),
    )

    # TODO: Validate
    def __init__(self, session: Session, show: Show) -> None:
        """Gather the show's episodes and the canonical ones they are read against."""
        self.session = session
        self.show = show
        episodes = [
            episode
            for season in show.active_children
            for episode in season.active_children
        ]
        # Split here and nowhere else, so what counts as a name is settled once
        # and each half is handed only the matchers that suit it.
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
        # Which season each episode of either side is under, read off the seasons
        # already in hand rather than back off each episode, since walking to a
        # season from the episode is a read apiece for rows that were reached
        # through that very season.
        self.season_numbers = {
            episode.id: season.season_number
            for parent in (show, *show.canonical_shows)
            for season in parent.active_children
            for episode in season.active_children
        }
        self._load_existing_links(
            [*self.episodes, *self.unnamed_episodes, *self.canonical_episodes],
        )
        # Read off the TMDB plugin the first time a matcher asks for them, since
        # two of them want the same translations and neither always runs.
        self._translated_forms: dict[uuid.UUID, frozenset[str]] | None = None
        # Read off the TMDB plugin the same way and for the same reason: three
        # matchers read the other orders and none of them always runs.
        self._alternate_numbers: dict[uuid.UUID, frozenset[int]] | None = None

    # TODO: Validate
    def _load_existing_links(self, episodes: Sequence[Episode]) -> None:
        """Settle what each episode already stands for without reading one at a time.

        Writing a link is a write the database works out the whole of only once
        it knows what the episode stood for before, so an episode whose link has
        not been read is one it goes and reads while writing - a query each, in
        the middle of the flush.

        A canonical row stands for nothing and is settled here rather than read
        at all: it says so outright, so there is no query to make for it, and the
        canonical rows are most of them.

        The rest are read together, which is one query rather than one apiece.
        """
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
        """Link all of the show's `Episode`s to canonical TMDB `Episode`s."""
        self.link_named_episodes(self.episodes)
        self.link_unnamed_episodes(self.unnamed_episodes)

    # TODO: Validate
    def link_named_episodes(self, episodes: list[Episode]) -> list[Episode]:
        """Read the episodes a website named through every matcher in turn.

        From the matcher that asks the most of a pair to the one that asks the
        least, each handed only what the one before it could not place, so the
        looser and costlier a matcher is the fewer episodes it has to read.
        """
        episodes = self._link_movie(episodes)
        episodes = self._link_name_and_numbering(episodes)
        episodes = self._link_plaintext_name_and_numbering(episodes)
        episodes = self._link_name_and_episode_number(episodes)
        episodes = self._link_plaintext_name_and_episode_number(episodes)
        episodes = self._link_description_and_episode_number(episodes)
        episodes = self._link_name_and_alternate_number(episodes)
        episodes = self._link_plaintext_name_and_alternate_number(episodes)
        episodes = self._link_similar_name_and_episode_number(episodes)
        episodes = self._link_similar_name_and_alternate_number(episodes)
        episodes = self._link_name(episodes)
        episodes = self._link_plaintext_name(episodes)
        episodes = self._link_description(episodes)
        return self._link_translated_name(episodes)

    # TODO: Validate
    def link_unnamed_episodes(self, episodes: list[Episode]) -> list[Episode]:
        """Read the episodes a website only numbered through the matchers left.

        Every matcher weighing a name is no use here and worse than none: a name
        that says nothing is as alike to one real name as to the next, and the
        closest of them is whichever happens to carry the word "Episode". What is
        left is where the episode sits and what it is about, which the website
        wrote down as truly as anybody.
        """
        episodes = self._link_movie(episodes)
        episodes = self._link_place_alone(episodes)
        episodes = self._link_description_and_episode_number(episodes)
        return self._link_description(episodes)

    # TODO: Validate
    @classmethod
    def _has_blacklisted_name(cls, episode: Episode) -> bool:
        """Whether the website named the episode at all."""
        name = episode.name
        if not name:
            return True
        return any(pattern.match(name) for pattern in cls.NAME_BLACKLIST)

    # TODO: Validate
    @staticmethod
    def _own_episode_numbers(tmdb_episode: Episode) -> Collection[int]:
        """The number a TMDB episode carries in the order its title is read in."""
        if tmdb_episode.episode_number is None:
            return ()
        return (tmdb_episode.episode_number,)

    # TODO: Validate
    @staticmethod
    def _canonical_episodes_by_name_and_number(
        canonical_episodes: Collection[Episode],
        name_of: Callable[[Episode], str | None],
        numbers_of: Callable[[Episode], Collection[int]],
    ) -> dict[tuple[str, int], Episode]:
        candidates: dict[tuple[str, int], Episode] = {}
        ambiguous: set[tuple[str, int]] = set()
        for tmdb_episode in canonical_episodes:
            name = name_of(tmdb_episode)
            if not name:
                continue
            for episode_number in numbers_of(tmdb_episode):
                pairing = (name, episode_number)
                if pairing in candidates:
                    ambiguous.add(pairing)
                    continue
                candidates[pairing] = tmdb_episode
        # Two TMDB episodes sharing a name and a number say nothing about which of
        # them an episode is, so neither is offered.
        for pairing in ambiguous:
            del candidates[pairing]
        return candidates

    # TODO: Validate
    @staticmethod
    def _canonical_episodes_by_numbering(
        canonical_episodes: Collection[Episode],
        name_of: Callable[[Episode], str | None],
        season_number_of: Callable[[Episode], int | None],
    ) -> dict[tuple[str, int, int], Episode]:
        candidates: dict[tuple[str, int, int], Episode] = {}
        ambiguous: set[tuple[str, int, int]] = set()
        for tmdb_episode in canonical_episodes:
            name = name_of(tmdb_episode)
            season_number = season_number_of(tmdb_episode)
            episode_number = tmdb_episode.episode_number
            if not name or season_number is None or episode_number is None:
                continue
            numbering = (name, season_number, episode_number)
            if numbering in candidates:
                ambiguous.add(numbering)
                continue
            candidates[numbering] = tmdb_episode
        # Two TMDB episodes filed under one name in one place say nothing about
        # which of them an episode is, so neither is offered.
        for numbering in ambiguous:
            del candidates[numbering]
        return candidates

    # TODO: Validate
    @staticmethod
    def _canonical_episodes_by_place(
        canonical_episodes: Collection[Episode],
        season_number_of: Callable[[Episode], int | None],
    ) -> dict[tuple[int, int], Episode]:
        candidates: dict[tuple[int, int], Episode] = {}
        ambiguous: set[tuple[int, int]] = set()
        for tmdb_episode in canonical_episodes:
            season_number = season_number_of(tmdb_episode)
            episode_number = tmdb_episode.episode_number
            if season_number is None or episode_number is None:
                continue
            place = (season_number, episode_number)
            if place in candidates:
                ambiguous.add(place)
                continue
            candidates[place] = tmdb_episode
        # Two TMDB episodes filed in one place say nothing about which of them an
        # episode is, so neither is offered.
        for place in ambiguous:
            del candidates[place]
        return candidates

    # TODO: Validate
    @staticmethod
    def _canonical_episodes_by_name(
        canonical_episodes: Collection[Episode],
        name_of: Callable[[Episode], str | None],
    ) -> dict[str, Episode]:
        candidates: dict[str, Episode] = {}
        ambiguous: set[str] = set()
        for tmdb_episode in canonical_episodes:
            name = name_of(tmdb_episode)
            if not name:
                continue
            if name in candidates:
                ambiguous.add(name)
                continue
            candidates[name] = tmdb_episode
        # Two TMDB episodes sharing a name say nothing about which of them an
        # episode is, so neither is offered.
        for name in ambiguous:
            del candidates[name]
        return candidates

    # TODO: Validate
    @staticmethod
    def _best_namesimilarity(
        episode: Episode,
        tmdb_episode: Episode,
        translated_forms: frozenset[str],
    ) -> float:
        """Return how alike the two are read across every name either carries."""
        best = similarity(episode.name, tmdb_episode.name)
        for form in plaintext_forms(episode.name):
            for translated_form in translated_forms:
                best = max(best, similarity(form, translated_form))
        return best

    # TODO: Validate
    def _translated_forms_cache(self) -> dict[uuid.UUID, frozenset[str]]:
        """Every spelling of every language's name for a TMDB episode, by episode.

        Kept on the session rather than on the linker, because a linker is built
        afresh for every show that is read and each of them wants the
        translations of the same canonical episodes. Reading them once per
        session is what keeps a run that reads one show a hundred times from
        reading them a hundred times.
        """
        cache: dict[uuid.UUID, frozenset[str]] = self.session.info.setdefault(
            "translated_episode_name_forms",
            {},
        )
        return cache

    # TODO: Validate
    def _alternate_numbers_cache(self) -> dict[int, dict[int, frozenset[int]]]:
        """Every number each TMDB episode carries in another order, by title.

        Kept on the session for the same reason the translations are: a linker is
        built afresh for every show that is read, and every copy of one title asks
        for the same title's orders.
        """
        cache: dict[int, dict[int, frozenset[int]]] = self.session.info.setdefault(
            "alternate_tmdb_episode_numbers",
            {},
        )
        return cache

    # TODO: Validate
    @staticmethod
    def _unlinked(episodes: list[Episode]) -> list[Episode]:
        """Leave only the episodes still waiting on a canonical episode."""
        return [episode for episode in episodes if not episode.canonical_episode_links]

    # TODO: Validate
    def _claim(self, episode: Episode, tmdb_episode: Episode, note: str) -> None:
        """Point the episode at the canonical episode and take it off the table.

        A canonical episode another of the show's episodes already names is
        handed to this one too. A listing carries the same episode twice often
        enough - Hulu's dubbed row and subtitled row of every episode of a title
        are both that episode - that the second row to answer to a record is
        another copy of it rather than a clash, and saying so is the answer a
        matcher worked out.

        The link is added to whatever the episode already stands for rather than
        put in its place: a matcher answering with a second record has found
        another episode the listing runs, and taking the first one off would
        leave the listing standing for whichever matcher spoke last.

        The record the link points at is set as well as its id, since what an
        episode has been given is read back off the links before any of this is
        written down. Leaving it to be filled in at the writing is what had a
        matched episode read as one still waiting: it was handed on to the
        matchers after, each of which gave it another canonical episode.

        Where the copy sits is carried onto the link, which is what a copy is
        ordered by once it has one; the column it was read off says where one
        website filed the row and cannot say where it sits under each of the
        episodes it stands for.
        """
        link = EpisodeCanonicalEpisode(
            episode_id=episode.id,
            canonical_episode_id=tmdb_episode.id,
            sort_order=episode.sort_order,
        )
        link.episode = episode
        link.canonical_episode = tmdb_episode
        episode.canonical_episode_links.append(link)
        episode.is_canonical = False
        episode.canonical_episode_note = note
        self.session.add(link)

    # TODO: Validate
    def _translated_name_forms(self) -> dict[uuid.UUID, frozenset[str]]:
        """Return every spelling of every language's name for each TMDB episode.

        An episode's translations are the one thing about a TMDB episode that is
        not stored alongside it, so they are read off the plugin rather than the
        row.

        Read once per session and remembered there, so the plugin is built and
        the translations are reached for only for the episodes nothing has read
        yet. A run that reads one show over and over reads them the first time
        and takes them off the session after that.

        Imported here rather than at the top of the module because the TMDB
        plugin is built on the base every plugin is, which reads this module in
        turn.
        """
        if self._translated_forms is not None:
            return self._translated_forms

        cache = self._translated_forms_cache()
        unread = [
            tmdb_episode
            for tmdb_episode in self.canonical_episodes
            if tmdb_episode.id not in cache
        ]
        if unread:
            from plugins.TMDB import TMDB  # noqa: PLC0415

            tmdb = TMDB(self.session)
            numberings = {
                tmdb_episode.id: self._episode_numbering(tmdb_episode)
                for tmdb_episode in unread
            }
            # Held for as long as the names are being read, because the session
            # keeps its records weakly and a row nothing is holding is dropped
            # and read again one at a time - which is what this read replaces.
            _rows = tmdb.preload_episode_translations(
                [
                    numbering
                    for numbering in numberings.values()
                    if numbering is not None
                ],
            )
            for tmdb_episode in unread:
                cache[tmdb_episode.id] = self._episode_name_forms(
                    tmdb,
                    numberings[tmdb_episode.id],
                )

        self._translated_forms = {
            tmdb_episode.id: cache[tmdb_episode.id]
            for tmdb_episode in self.canonical_episodes
        }
        return self._translated_forms

    # TODO: Validate
    def _alternate_episode_numbers(self) -> dict[uuid.UUID, frozenset[int]]:
        """Return every number each canonical episode carries in another order.

        The orders are TMDB's own and are read off the plugin, since a row holds
        the numbering of the one order its title is stored in and nothing of the
        rest. Every title the show is a copy of is read, so a listing that mixes
        titles is matched against the orders of each of them.

        Read once per title per session and remembered there, so a run that reads
        one title over and over reads its orders the first time and takes them
        off the session after that.

        Imported here rather than at the top of the module because the TMDB
        plugin is built on the base every plugin is, which reads this module in
        turn.
        """
        if self._alternate_numbers is not None:
            return self._alternate_numbers

        from plugins.TMDB import TMDB  # noqa: PLC0415

        cache = self._alternate_numbers_cache()
        tmdb = TMDB(self.session)
        by_tmdb_id: dict[int, frozenset[int]] = {}
        for canonical_show in self.show.canonical_shows:
            tmdb_show_id = tmdb_id_of(canonical_show.key, SHOW_LEVEL)
            media_type = tmdb_media_type_of(canonical_show.key, SHOW_LEVEL)
            # A film is one episode of one season however it is read, so there is
            # no other order for it to be in.
            if tmdb_show_id is None or media_type is not MediaType.tv:
                continue
            if tmdb_show_id not in cache:
                cache[tmdb_show_id] = tmdb.alternate_episode_numbers(tmdb_show_id)
            by_tmdb_id |= cache[tmdb_show_id]

        self._alternate_numbers = {}
        for tmdb_episode in self.canonical_episodes:
            tmdb_episode_id = tmdb_id_of(tmdb_episode.key, EPISODE_LEVEL)
            if tmdb_episode_id is None:
                continue
            if numbers := by_tmdb_id.get(tmdb_episode_id):
                self._alternate_numbers[tmdb_episode.id] = numbers
        return self._alternate_numbers

    # TODO: Validate
    def _alternate_numbers_of(self, tmdb_episode: Episode) -> Collection[int]:
        """The numbers a TMDB episode carries in TMDB's other orders of its title."""
        return self._alternate_episode_numbers().get(tmdb_episode.id, frozenset())

    # TODO: Validate
    @staticmethod
    def _episode_numbering(tmdb_episode: Episode) -> tuple[int, int, int] | None:
        """What TMDB is asked about one episode by, where it can be asked at all.

        An episode whose title, season or number is not known is one TMDB has no
        answer for, and says so by having no numbering rather than a partial one.
        """
        season = tmdb_episode.season
        tmdb_show_id = tmdb_id_of(season.show.key, SHOW_LEVEL)
        if (
            tmdb_show_id is None
            or season.season_number is None
            or tmdb_episode.episode_number is None
        ):
            return None
        return (tmdb_show_id, season.season_number, tmdb_episode.episode_number)

    # TODO: Validate
    @staticmethod
    def _episode_name_forms(
        tmdb: TMDB,
        numbering: tuple[int, int, int] | None,
    ) -> frozenset[str]:
        """Return every spelling of every language's name for one TMDB episode.

        An episode TMDB cannot be asked about has no names rather than none
        recorded, which is the same thing to everything that reads them and is
        what keeps it from being asked about again.
        """
        if numbering is None:
            return frozenset()
        return frozenset(
            form
            for name in tmdb.translated_episode_names(*numbering)
            for form in plaintext_forms(name)
        )

    def _link_movie(self, episodes: list[Episode]) -> list[Episode]:
        """Link movies."""
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
        if not episode.canonical_episode_locked:
            self._claim(episode, canonical_episode, "Automatic: Movie match")
        return []

    # TODO: Validate
    def _link_place_alone(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the one filed where it is.

        Where the episode sits is the whole of what there is to match on: the
        episode of the same season and the same number is it. TMDB's own name for
        that episode is no part of the reading, since the two were never going to
        agree on a name this website never had.

        Two TMDB episodes filed in one place, or none at all, leaves the episode
        where it was for the matchers below to read.
        """
        by_place = self._canonical_episodes_by_place(
            self.canonical_episodes,
            self._season_number_of,
        )
        for episode in episodes:
            season_number = self._season_number_of(episode)
            if season_number is None or episode.episode_number is None:
                continue
            if match := by_place.get((season_number, episode.episode_number)):
                self._claim(episode, match, "Automatic: Numbering match")
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_name_and_number(
        self,
        episodes: list[Episode],
        name_of: Callable[[Episode], str | None],
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> list[Episode]:
        """Point each episode at the TMDB episode of its name and one of its numbers."""
        sorted_canonical_episodes = self._canonical_episodes_by_name_and_number(
            self.canonical_episodes,
            name_of,
            numbers_of,
        )
        for episode in episodes:
            pairing = (name_of(episode), episode.episode_number)
            if match := sorted_canonical_episodes.get(pairing):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
                self._claim(episode, match, note)
        return self._unlinked(episodes)

    # TODO: Validate
    def _season_number_of(self, episode: Episode) -> int | None:
        """The season an episode of either side is filed under."""
        return self.season_numbers.get(episode.id)

    # TODO: Validate
    def _link_numbering(
        self,
        episodes: list[Episode],
        name_of: Callable[[Episode], str | None],
        note: str,
    ) -> list[Episode]:
        """Point each episode at the TMDB episode of its name, season and number."""
        sorted_canonical_episodes = self._canonical_episodes_by_numbering(
            self.canonical_episodes,
            name_of,
            self._season_number_of,
        )
        for episode in episodes:
            numbering = (
                name_of(episode),
                self._season_number_of(episode),
                episode.episode_number,
            )
            if match := sorted_canonical_episodes.get(numbering):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
                self._claim(episode, match, note)
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_name_and_numbering(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode of its name, season and number.

        A title whose episodes are called nothing but where they are - "Episode
        4" - has that name once a season, so the name and the episode number
        together still pick out one episode per season and none of the matchers
        reading those two alone can say which season's it is. Read the season as
        well and the pair line up: same name, same place, same episode.
        """
        return self._link_numbering(
            episodes,
            lambda tmdb_episode: tmdb_episode.name,
            "Automatic: Name and full numbering match",
        )

    # TODO: Validate
    def _link_plaintext_name_and_numbering(
        self, episodes: list[Episode]
    ) -> list[Episode]:
        """Point each episode at the TMDB episode of its name, season and number.

        The same as matching on a name and a full numbering, with the case,
        punctuation and spacing of the name taken out of it.
        """
        return self._link_numbering(
            episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.name),
            "Automatic: Plaintext name and full numbering match",
        )

    # TODO: Validate
    def _link_name_and_episode_number(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode of the same name and number."""
        return self._link_name_and_number(
            episodes,
            lambda tmdb_episode: tmdb_episode.name,
            self._own_episode_numbers,
            "Automatic: Name and number match",
        )

    # TODO: Validate
    def _link_plaintext_name_and_episode_number(
        self, episodes: list[Episode]
    ) -> list[Episode]:
        """Point each episode at the TMDB episode of the same name and number.

        The names are compared with their case, punctuation and spacing taken
        out, so "The One With the Cat" and "the one with the cat!" are the one
        name they are both a spelling of and the episode is matched rather than
        left waiting.
        """
        return self._link_name_and_number(
            episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.name),
            self._own_episode_numbers,
            "Automatic: Plaintext name and number match",
        )

    # TODO: Validate
    def _link_description_and_episode_number(
        self, episodes: list[Episode]
    ) -> list[Episode]:
        """Point each episode at the TMDB episode described the same under its number.

        A website that renames an episode - translating it, shortening it, or
        calling it nothing but where it is - still tends to carry the summary
        TMDB carries, since that is one paragraph nobody rewrites. Where the
        names have parted company the descriptions have not, and a paragraph is
        long enough that two episodes sharing one word for word are the same
        episode.

        Read after the names of the same kind, since a name is what an episode is
        called and a description is only what it is about. Two TMDB episodes
        described the same - the placeholder a title carries before it airs is
        the same paragraph on every one of them - say nothing about which of them
        an episode is, so neither is offered.
        """
        return self._link_name_and_number(
            episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.description),
            self._own_episode_numbers,
            "Automatic: Description and number match",
        )

    # TODO: Validate
    def _link_name_and_alternate_number(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode of its name, in any other order.

        The number the website wrote down is read against every order TMDB holds
        for the title rather than against the one the title is stored in, so an
        episode numbered by the DVD order or counted straight through the run is
        matched by the number that order gives it.
        """
        if not episodes:
            return episodes
        return self._link_name_and_number(
            episodes,
            lambda tmdb_episode: tmdb_episode.name,
            self._alternate_numbers_of,
            "Automatic: Name and alternate order number match",
        )

    # TODO: Validate
    def _link_plaintext_name_and_alternate_number(
        self, episodes: list[Episode]
    ) -> list[Episode]:
        """Point each episode at the TMDB episode of its name, in any other order.

        The same as matching on a name and another order's number, with the case,
        punctuation and spacing of the name taken out of it.
        """
        if not episodes:
            return episodes
        return self._link_name_and_number(
            episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.name),
            self._alternate_numbers_of,
            "Automatic: Plaintext name and alternate order number match",
        )

    # TODO: Validate
    def _link_name(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode of the same name.

        The numbering is no part of it, so an episode a website filed under a
        number of its own is still matched by the one thing the two of them agree
        on.
        """
        sorted_canonical_episodes = self._canonical_episodes_by_name(
            self.canonical_episodes,
            lambda tmdb_episode: tmdb_episode.name,
        )
        for episode in episodes:
            if match := sorted_canonical_episodes.get(episode.name):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
                self._claim(episode, match, "Automatic: Name match")
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_plaintext_name(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode of the same name.

        Neither the numbering nor the case, punctuation and spacing of the name
        are any part of it, which is the loosest either of them can be matched
        on.
        """
        sorted_canonical_episodes = self._canonical_episodes_by_name(
            self.canonical_episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.name),
        )
        for episode in episodes:
            if match := sorted_canonical_episodes.get(plaintext(episode.name)):
                self._claim(episode, match, "Automatic: Plaintext name match")
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_description(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode described the same.

        The numbering is no part of it, so an episode a website filed under a
        number of its own is still matched by the paragraph the two of them
        agree on. The loosest a description can be read, and read after the names
        are for the same reason they are: what an episode is called says more
        about which it is than what it is about.
        """
        sorted_canonical_episodes = self._canonical_episodes_by_name(
            self.canonical_episodes,
            lambda tmdb_episode: plaintext(tmdb_episode.description),
        )
        for episode in episodes:
            if match := sorted_canonical_episodes.get(plaintext(episode.description)):
                self._claim(episode, match, "Automatic: Description match")
        return self._unlinked(episodes)

    # TODO: Validate
    def _link_translated_name(self, episodes: list[Episode]) -> list[Episode]:
        """Point each episode at the TMDB episode named that in any language.

        A website carries the name the episode is known by where it is watched,
        which is the Japanese name of a Japanese title on one site and the
        English name of the same episode on the next, and neither is the name the
        other wrote down. TMDB holds every language's name for an episode, so an
        episode is matched against all of them rather than against the one
        language its row was read in.

        Each name is compared as every spelling it could be written in, so a name
        written in kana on one side and romanised on the other is still the one
        name the two of them are. Two TMDB episodes answering to the same name
        say nothing about which of them an episode is, so neither is taken.
        """
        if not episodes:
            return episodes

        forms_by_tmdb_episode = self._translated_name_forms()
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
    def _link_similar_name_and_alternate_number(
        self, episodes: list[Episode]
    ) -> list[Episode]:
        """Point each episode at the closest named TMDB episode of another order.

        The same as matching on a similar name and a number, with the number read
        against every order TMDB holds for the title rather than against the one
        the title is stored in.
        """
        if not episodes:
            return episodes
        return self._link_similar_name(
            episodes,
            self._alternate_numbers_of,
            "Automatic: Similar name and alternate order number match",
        )

    # TODO: Validate
    def _link_similar_name_and_episode_number(
        self,
        episodes: list[Episode],
    ) -> list[Episode]:
        """Point each episode at the closest named TMDB episode of its number.

        The name a website wrote down is the name of the episode as somebody
        typed it, which is the official name with a word dropped, a subtitle
        added or a spelling of its own, and none of those are the name TMDB holds
        letter for letter. Every name either side carries is read here, the
        official one and every language's, and the closest of them decides it.

        Only episodes sharing a number are considered, so the numbering carries
        the weight the name no longer can. A name has to be alike enough to mean
        something and has to be clearly ahead of the next best, or the episode is
        left waiting.
        """
        return self._link_similar_name(
            episodes,
            self._own_episode_numbers,
            "Automatic: Similar name and number match",
        )

    # TODO: Validate
    def _link_similar_name(
        self,
        episodes: list[Episode],
        numbers_of: Callable[[Episode], Collection[int]],
        note: str,
    ) -> list[Episode]:
        """Point each episode at the closest named TMDB episode carrying its number."""
        numbered_episodes = [
            episode for episode in episodes if episode.episode_number is not None
        ]
        if not numbered_episodes:
            return episodes

        forms_by_tmdb_episode = self._translated_name_forms()
        for episode in numbered_episodes:
            scored = sorted(
                (
                    (
                        self._best_namesimilarity(
                            episode,
                            tmdb_episode,
                            forms_by_tmdb_episode.get(tmdb_episode.id, frozenset()),
                        ),
                        tmdb_episode,
                    )
                    for tmdb_episode in self.canonical_episodes
                    if episode.episode_number in numbers_of(tmdb_episode)
                ),
                key=lambda scoring: scoring[0],
                reverse=True,
            )
            if not scored or scored[0][0] < self.SIMILAR_NAME_FLOOR:
                continue
            if len(scored) > 1 and scored[0][0] - scored[1][0] < self.SIMILAR_NAME_LEAD:
                continue

            self._claim(episode, scored[0][1], note)
        return self._unlinked(episodes)


# What a person settles by hand, rather than what the matchers work out.
# The same linking, decided rather than read: a record chosen for one
# episode, an address pasted in, a link taken back, or an episode settled as
# one TMDB has no record of.


# TODO: Validate
def _import_tmdb_url(session: Session, url: str) -> Show:
    """Read the title a themoviedb.org address is under in, and return its row.

    Which half of the catalogue an address names and which title is the plugin's
    to read, so the address is handed over whole rather than taken apart first. A
    season and an episode are under the title rather than beside it, so an
    address naming one reads the title in exactly as the title's own page would.

    Imported here rather than at the top of the module because the TMDB plugin
    is built on the base every plugin is, which reads this module in turn.
    """
    from plugins.TMDB import TMDB  # noqa: PLC0415

    imported = TMDB(session).import_url(url)
    statement = select(Show).where(
        is_canonical(Show),
        Show.key == imported[0].show_key,
    )
    return session.exec(statement).one()


# TODO: Validate
def link_episode_using_tmdb_url(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    """Point `episode` at the TMDB record a themoviedb.org address names.

    Only a film's page and a series episode's page are taken, since they are the
    addresses that name one record: a series page names a title rather than any
    of its episodes, and a season's names a run of them, so neither says what
    `episode` is a copy of. Which of the two was given is settled here, and the
    address is handed on to whichever reads it.
    """
    address = url.strip()
    if found := _SERIES_EPISODE_URL.search(address):
        return _link_episode_using_tmdb_episode(session, episode, address, found)
    if _FILM_URL.search(address):
        return _link_episode_using_tmdb_movie(session, episode, address)

    raise HTTPException(
        status_code=400,
        detail=f"{url} is not the address of a TMDB film or series episode",
    )


# TODO: Validate
def _link_episode_using_tmdb_episode(
    session: Session,
    episode: Episode,
    url: str,
    found: re.Match[str],
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)
    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(Episode),
            Season.show_id == canonical_show.id,
            Season.season_number == int(found["season_number"]),
            Episode.episode_number == int(found["episode_number"]),
        ),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def _link_episode_using_tmdb_movie(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)

    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(is_canonical(Episode), Season.show_id == canonical_show.id),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def link_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> Episode:
    """Point every listing of `episode`'s media at a TMDB episode.

    A `User` saying which TMDB episode this is has said it of the media rather
    than of the one row they happened to be looking at, and `watch_identifier`
    is what says two rows are of the same media. So every row carrying that
    identifier is pointed at the record together, which is what stops the same
    decision having to be made again for each website carrying the episode.
    """
    for same_media in _episodes_sharing_identifier(session, episode):
        _link_one_episode(session, same_media, canonical_episode)

    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _episodes_sharing_identifier(session: Session, episode: Episode) -> list[Episode]:
    """Return every stored listing of the media `episode` is a listing of."""
    return list(
        session.exec(
            select(Episode).where(
                Episode.watch_identifier == episode.watch_identifier,
                col(Episode.deleted_at).is_(None),
            ),
        ).all(),
    )


# TODO: Validate
def _link_one_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> None:
    """Point one `Episode` at a TMDB episode, and its show at the title holding it.

    Added to whatever the row already stands for rather than put in its place. A
    website runs two episodes together in one listing often enough - a
    double-length first airing, a recap paired with the episode it recaps - that
    a second record chosen for a row is another episode the row is of, and
    dropping the first would leave the row standing for whichever was chosen
    last. Taking one off is `unlink_episode`, which is a thing to ask for.

    Two websites' rows standing for one record is what makes them a single
    episode to watch, so another row already on this record is no clash either
    and is left where it is.
    """
    add_canonical_show(session, episode.season.show, canonical_episode.season.show)

    if canonical_episode.id not in episode.canonical_episode_ids:
        session.add(
            EpisodeCanonicalEpisode(
                episode_id=episode.id,
                canonical_episode_id=canonical_episode.id,
                sort_order=episode.sort_order,
            ),
        )

    episode.is_canonical = False
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Selection"
    session.add(episode)


# TODO: Validate
def unlink_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode | None = None,
) -> Episode:
    """Take `episode` off a TMDB episode it was pointed at, or off all of them.

    One record where one is named and every one of them where none is, since a
    row standing for two is asked to let go of one of them and a row being
    unlinked outright is asked to let go of the lot.

    A row left standing for nothing is a row nothing has settled rather than one
    settled at nothing: a link taken back is a link that should not have been
    made, so the lock and the note go with the last of them and the next import
    is free to work out its own again. A row still standing for something keeps
    both, having lost none of what settled it.
    """
    for link in list(episode.canonical_episode_links):
        if (
            canonical_episode is None
            or link.canonical_episode_id == canonical_episode.id
        ):
            session.delete(link)
    session.flush()
    session.expire(episode, ["canonical_episode_links"])

    if not episode.canonical_episode_links:
        episode.is_canonical = True
        episode.canonical_episode_locked = False
        episode.canonical_episode_note = None
        session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def mark_episode_absent_from_tmdb(session: Session, episode: Episode) -> Episode:
    """Settle `episode` as one TMDB has no record of.

    Pointed at nothing and locked there, which is what says the emptiness was
    decided rather than not yet worked out: an import leaves an episode it could
    not place pointing at nothing too, and only the lock tells the two apart. The
    note says who decided, so it carries the manual prefix the same way a link
    chosen by hand does.

    Every link it carried comes off: an episode TMDB has no record of stands for
    nothing, whatever was worked out for it before.
    """
    for link in list(episode.canonical_episode_links):
        session.delete(link)
    session.flush()
    session.expire(episode, ["canonical_episode_links"])

    episode.is_canonical = True
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Not on TMDB"
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode
