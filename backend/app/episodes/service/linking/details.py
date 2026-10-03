# TODO: Validate
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.service.names.forms import (
    get_cased_episode_name,
    get_normalized_episode_name,
)
from app.episodes.service.names.scored_text import (
    description_for_scoring,
    name_for_scoring,
)

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable
    from datetime import datetime


# TODO: Validate
class MatchKind(StrEnum):
    TFIDF_NAME = "TF-IDF name"
    EMBEDDING_NAME = "Embedding name"
    TFIDF_DESCRIPTION = "TF-IDF description"
    EMBEDDING_DESCRIPTION = "Embedding description"


# TODO: Validate
@dataclass(frozen=True, slots=True)
class LinkedEpisodeRow:
    name: str
    cased_name: str
    season_number: int | None
    episode_number: int
    tmdb_episode_id: uuid.UUID


# TODO: Validate
@dataclass(slots=True)
class EpisodeDetails:
    model: Episode
    id: uuid.UUID
    key: str
    name: str | None
    description: str
    episode_number: int | None
    season_number: int | None
    title_name: str | None
    season_name: str | None = None
    series_name: str | None = None
    absolute_number: int | None = None
    linked_episodes: list[EpisodeDetails] = field(default_factory=list)
    matches: dict[MatchKind, EpisodeMatch] = field(default_factory=dict)
    normalized_name: str = field(init=False)
    cased_name: str = field(init=False)
    name_for_scoring: str = field(init=False)

    # TODO: Validate
    def __post_init__(self) -> None:
        self.description = description_for_scoring(self.description)
        self.title_name = self.title_name.strip() if self.title_name else None
        self.season_name = self.season_name.strip() if self.season_name else None
        self.series_name = self.series_name.strip() if self.series_name else None
        self.normalized_name = get_normalized_episode_name(
            self.name,
            self.title_name,
            self.season_name,
            self.series_name,
        )
        self.cased_name = get_cased_episode_name(
            self.name,
            self.title_name,
            self.season_name,
            self.series_name,
        )
        self.name_for_scoring = name_for_scoring(
            self.name,
            self.title_name,
            self.season_name,
            self.series_name,
        )


# TODO: Validate
@dataclass(slots=True)
class TmdbEpisodeDetails(EpisodeDetails):
    pass


# TODO: Validate
@dataclass(slots=True)
class SourceEpisodeDetails(EpisodeDetails):
    tmdb_episode_validated_at: datetime | None = None
    link_note: str | None = None

    # TODO: Validate
    def link_to(self, tmdb_episode: EpisodeDetails, note: str) -> None:
        """Note on both episodes that they are linked to each other, and why."""
        self.linked_episodes.append(tmdb_episode)
        self.link_note = note
        tmdb_episode.linked_episodes.append(self)

    # TODO: Validate
    def save_links(self) -> None:
        if self.tmdb_episode_validated_at is not None:
            return

        # Existing links are re-used to improve performance because it is faster to
        # do nothing at all if the link already exists.
        existing_links = {
            link.tmdb_episode_id: link for link in self.model.tmdb_episode_links
        }
        # Performance is also better if a new list is built to replace the old one
        # instead of clearing the old one out and appending to it.
        tmdb_episode_links: list[EpisodeTmdbEpisode] = []
        for tmdb_episode in self.linked_episodes:
            if link := existing_links.get(tmdb_episode.id):
                if link.note != self.link_note:
                    link.note = self.link_note
            else:
                link = EpisodeTmdbEpisode(
                    episode_id=self.id,
                    tmdb_episode_id=tmdb_episode.id,
                    note=self.link_note,
                )
            tmdb_episode_links.append(link)
        self.model.tmdb_episode_links = tmdb_episode_links


# TODO: Validate
@dataclass(slots=True)
class SplitNameNormalizers:
    text_of: Callable[[EpisodeDetails], str]
    label: str
    normalize: Callable[[str], str] = str


# TODO: Validate
@dataclass(slots=True)
class EpisodeMatch:
    score: float
    episodes: list[EpisodeDetails]
    valid: bool
    runner_up: float

    # TODO: Validate
    @property
    def episode(self) -> EpisodeDetails:
        return self.episodes[0]

    # TODO: Validate
    def picked(self, episode: EpisodeDetails) -> bool:
        return any(other is episode for other in self.episodes)


# TODO: Validate
@dataclass(slots=True)
class CombinedMatch:
    score: float
    episodes: list[EpisodeDetails]
    runner_up: float
    kind_scores: tuple[tuple[MatchKind, float], ...]

    # TODO: Validate
    @property
    def episode(self) -> EpisodeDetails:
        return self.episodes[0]

    # TODO: Validate
    def picked(self, episode: EpisodeDetails) -> bool:
        return any(other is episode for other in self.episodes)


# TODO: Validate
def link_combined_to_part(
    combined_episode: EpisodeDetails,
    part_episode: EpisodeDetails,
    note: str,
) -> None:
    if isinstance(combined_episode, SourceEpisodeDetails):
        combined_episode.link_to(part_episode, note)
    elif isinstance(part_episode, SourceEpisodeDetails):
        part_episode.link_to(combined_episode, note)
