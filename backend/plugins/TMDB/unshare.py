# TODO: Validate
"""Let go of the episodes an import left sharing one record.

One canonical episode is one episode to watch, so two episodes of a single show
pointing at it is the matching having put both of them on a record that at most
one of them is.
"""

import uuid
from collections import Counter, defaultdict

from loguru import logger
from sqlmodel import Session

from app.episodes.models import MANUAL_NOTES, Episode
from app.episodes.tmdb_matches import absolute_numbers
from app.media.canonical_metadata import canonical_episode_of
from app.shows.models import Show


# TODO: Validate
def _numberings(show: Show) -> list[tuple[uuid.UUID, int | None, int | None]]:
    """Return how a title numbers each of its episodes, for counting them through."""
    return [
        (episode.id, season.season_number, episode.episode_number)
        for season in show.active_children
        for episode in season.active_children
    ]


# TODO: Validate
def _canonical_numberings(
    canonical_show: Show,
) -> list[tuple[uuid.UUID, int | None, int | None]]:
    """Return how the title itself numbers its episodes, for counting them through.

    The canonical mirror of `_numberings`. Canonical rows are never soft
    deleted, so every season and episode under the title counts.
    """
    return [
        (episode.id, season.season_number, episode.episode_number)
        for season in canonical_show.seasons
        for episode in season.episodes
    ]


# TODO: Validate
def _is_settled_by_hand(episode: Episode) -> bool:
    """Report whether a `User` settled which episode this is a copy of."""
    return (
        episode.canonical_episode_locked
        and episode.canonical_episode_note in MANUAL_NOTES
    )


# TODO: Validate
def unshare_canonical_episodes(session: Session, show: Show) -> None:
    """Unlink the episodes of `show` that ended up pointing at the same record.

    One canonical episode is one episode to watch, so two episodes of a
    single show pointing at it is the matching having put both of them on a
    record that at most one of them is. Neither is the one to keep, so each
    is let go of and what they shared is written into the note rather than
    lost. A copy left pointing at nothing is given a row of its own by
    `reconcile_show`, which runs straight after this.

    Only what a `User` settled is left alone, which is also what decides a
    clash between their episode and any other in their favour. A lock the
    import made itself is no help here: it was made on evidence that has
    turned out to fit two episodes, so it goes along with the link.

    An episode numbered the way the record numbers it keeps the link, since
    that tells it apart from the others rather than leaving every one of
    them a guess, and only the rest are let go of.
    """
    episodes = [
        episode
        for season in show.active_children
        for episode in season.active_children
        if episode.canonical_episode_id is not None
    ]
    counts = Counter(episode.canonical_episode_id for episode in episodes)
    shared = {canonical_id for canonical_id, count in counts.items() if count > 1}
    if not shared:
        return

    clashing_by_canonical: dict[uuid.UUID, list[Episode]] = defaultdict(list)
    for episode in episodes:
        if episode.canonical_episode_id in shared:
            clashing_by_canonical[episode.canonical_episode_id].append(episode)

    for canonical_id, clashing in clashing_by_canonical.items():
        keeper = _kept_from_clash(session, canonical_id, clashing)
        for episode in clashing:
            if episode is keeper or _is_settled_by_hand(episode):
                continue
            logger.info(f"Unsharing {canonical_id} from episode {episode.key}")
            removed = f"Removed {canonical_id}, which another episode was given too"
            # What the episode was matched on is kept behind the removal
            # rather than written over it, since how it came to be linked is
            # most of what says whether it should have kept the link.
            previous = episode.canonical_episode_note
            episode.canonical_episode_note = (
                f"{removed}. {previous}" if previous else removed
            )
            episode.canonical_episode_id = None
            episode.canonical_episode_locked = False


# TODO: Validate
def _kept_from_clash(
    session: Session,
    canonical_id: uuid.UUID,
    clashing: list[Episode],
) -> Episode | None:
    """Return the one episode of a clash numbered the way TMDB numbers it.

    The episodes on one record are all guesses until something tells them
    apart, and the numbering is that: whatever put the others there was a
    name or a count that has turned out to fit more than one of them.

    A website filing a special among a season's episodes gives it the same
    season and episode number as the episode it sits beside, so how far into
    the title each one is counts as well. That is the number the two of them
    differ by, and without it neither is told from the other.

    Only ever a single episode, since two the numbering fits are no more
    told apart than none were. A `User` settling one of them decides the
    clash by itself, so nothing is kept here while one of them is theirs.
    """
    if any(_is_settled_by_hand(episode) for episode in clashing):
        return None

    counterpart = canonical_episode_of(session, canonical_id)
    if counterpart is None:
        return None
    tmdb_episode, tmdb_season, tmdb_show = counterpart

    tmdb_absolute = absolute_numbers(_canonical_numberings(tmdb_show)).get(
        tmdb_episode.id,
    )
    source_absolute = absolute_numbers(_numberings(clashing[0].season.show))

    numbered = [
        episode
        for episode in clashing
        if episode.episode_number == tmdb_episode.episode_number
        and episode.season.season_number == tmdb_season.season_number
        and source_absolute.get(episode.id) == tmdb_absolute
    ]
    return numbered[0] if len(numbered) == 1 else None
