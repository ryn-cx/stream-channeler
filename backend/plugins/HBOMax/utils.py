# TODO: Validate
"""What every other part of the plugin reads an HBO Max title by."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from minbo.movie.models import Idref14 as MovieContent
    from minbo.movie.models import MovieModel
    from minbo.show.models import Episode1 as Episode
    from minbo.show.models import Idref14 as TitleContent
    from minbo.show.models import Season1 as Season
    from minbo.show.models import ShowModel


# TODO: Validate
@runtime_checkable
class MappedContent(Protocol):
    release_year: str
    credits: object


# TODO: Validate
@runtime_checkable
class MappedRelatedItem(Protocol):
    hbomax_id: UUID
    type: str


# TODO: Validate
@runtime_checkable
class MappedCarousel(Protocol):
    collection_id: str
    items: list[object]


# TODO: Validate
@runtime_checkable
class MappedCarouselItem(Protocol):
    hbomax_id: UUID
    category: str


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://play.hbomax.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"show/{title_key}")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movie/{movie_key}")


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def build_episode_key(season_key: str, episode_number: int) -> str:
    return f"{season_key}:{episode_number}"


# TODO: Validate
def title_content(title: ShowModel) -> TitleContent:
    return _mapped_content(title)  # type: ignore[return-value]


# TODO: Validate
def movie_content(movie: MovieModel) -> MovieContent:
    return _mapped_content(movie)  # type: ignore[return-value]


# TODO: Validate
def season_numbers(title: ShowModel) -> list[int]:
    return [season.season_number for season in title_content(title).seasons]


# TODO: Validate
def season_entry(title: ShowModel, season_number: int) -> Season:
    for season in title_content(title).seasons:
        if season.season_number == season_number:
            return season
    msg = f"Season {season_number} not found."
    raise ValueError(msg)


# TODO: Validate
def season_episodes(season: ShowModel, season_number: int) -> list[Episode]:
    for entry in title_content(season).seasons:
        if entry.season_number == season_number:
            return entry.episodes
    msg = f"Season {season_number} not found."
    raise ValueError(msg)


# TODO: Validate
def related_urls(page: ShowModel | MovieModel) -> list[str]:
    urls: dict[str, None] = {}
    for _, value in page.props.page_props.mapped_data:
        for item in value if isinstance(value, list) else []:
            if isinstance(item, MappedRelatedItem):
                key = str(item.hbomax_id)
                url = title_url(key) if item.type == "series" else movie_url(key)
                urls[url] = None
    urls.update(_carousel_urls(page, site_wide=False))
    return list(urls)


# TODO: Validate
def page_urls(page: ShowModel | MovieModel) -> list[str]:
    urls: dict[str, None] = dict.fromkeys(related_urls(page))
    urls.update(_carousel_urls(page, site_wide=True))
    return list(urls)


# TODO: Validate
def _carousel_urls(
    page: ShowModel | MovieModel,
    *,
    site_wide: bool,
) -> dict[str, None]:
    urls: dict[str, None] = {}
    for _, value in page.props.page_props.mapped_data:
        if not isinstance(value, MappedCarousel):
            continue
        is_site_wide = value.collection_id in ("13187", "14196")
        if is_site_wide != site_wide:
            continue
        for item in value.items:
            if isinstance(item, MappedCarouselItem):
                key = str(item.hbomax_id)
                url = title_url(key) if item.category == "Series" else movie_url(key)
                urls[url] = None
    return urls


# TODO: Validate
def _mapped_content(page: ShowModel | MovieModel) -> MappedContent:
    for _, value in page.props.page_props.mapped_data:
        if isinstance(value, MappedContent):
            return value

    msg = "No title is described by the page's mapped data."
    raise ValueError(msg)
