# TODO: Validate
"""What every other part of the plugin reads a Netflix title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from meshfilm.preview_modal_episode_selector.models import (
        Node as SeasonNode,
    )
    from meshfilm.preview_modal_episode_selector.models import (
        PreviewModalEpisodeSelectorModel,
    )
    from meshfilm.preview_modal_episode_selector_season_episodes.models import (
        Node as EpisodeNode,
    )
    from meshfilm.preview_modal_episode_selector_season_episodes.models import (
        PreviewModalEpisodeSelectorSeasonEpisodesModel,
    )


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://netflix.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"title/{title_key}")


# TODO: Validate
def episode_url(episode_key: str) -> str:
    return build_url(f"watch/{episode_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"search?q={quote_plus(query)}")


# TODO: Validate
def build_season_key(title_key: str, season_id: str | int) -> str:
    return f"{title_key}:{season_id}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, season_id = season_key.partition(":")
    return title_key, season_id


# TODO: Validate
def ordered_seasons(seasons: PreviewModalEpisodeSelectorModel) -> list[SeasonNode]:
    video = seasons.data.videos[0]
    if video.seasons is None:
        return []
    return [edge.node for edge in video.seasons.edges]


# TODO: Validate
def season_episodes(
    episodes: PreviewModalEpisodeSelectorSeasonEpisodesModel,
) -> list[EpisodeNode]:
    video = episodes.data.videos[0]
    if video.episodes is None:
        return []
    return [edge.node for edge in video.episodes.edges]
