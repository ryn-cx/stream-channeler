# TODO: Validate
"""What every other part of the plugin reads a Netflix title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from plugins.Netflix.constants import SEARCH_MEDIA_TYPES, WEEKDAYS

if TYPE_CHECKING:
    from meshfilm.lodp_title_and_plans_page.models import (
        LodpTitleAndPlansPageModel,
    )
    from meshfilm.lodp_title_and_plans_page.models import (
        Video1 as TitleVideo,
    )
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
    from meshfilm.search_page_results.models import SearchPageResultsModel


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
def title_video(
    title: LodpTitleAndPlansPageModel,
    title_key: str,
) -> TitleVideo:
    video = next(
        (video for video in title.data.videos if video.video_id == int(title_key)),
        None,
    )
    if video is None:
        msg = f"No title found for {title_key}"
        raise ValueError(msg)
    return video


# TODO: Validate
def is_movie(title: LodpTitleAndPlansPageModel, title_key: str) -> bool:
    return title_video(title, title_key).field__typename == "Movie"


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


# TODO: Validate
def first_search_result_key(results: SearchPageResultsModel) -> str | None:
    """Return the first movie or TV title in a page of search results.

    Netflix returns movies and titles intermixed. Suggestion entities
    (collections, autocomplete) carry no title and are skipped.
    """
    for section in results.data.page.sections.edges:
        for entity in section.node.entities.edges:
            unified_entity = entity.node.unified_entity
            if unified_entity is None:
                continue
            if unified_entity.field__typename not in SEARCH_MEDIA_TYPES:
                continue
            return str(unified_entity.video_id)
    return None


# TODO: Validate
def upcoming_weekday(video: TitleVideo) -> int | None:
    """Return the weekday an upcoming episode is scheduled for, or None if none.

    Netflix surfaces this as a tagline message (e.g. "New Episode Coming
    Thursday"); a title with nothing upcoming has an empty tagline.
    """
    for tagline in video.tagline_messages:
        for name, weekday in WEEKDAYS.items():
            if name in tagline.tagline:
                return weekday
    return None
