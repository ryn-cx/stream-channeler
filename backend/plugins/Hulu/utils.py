# TODO: Validate
"""What every other part of the plugin reads a title by."""

from urllib.parse import quote
from uuid import UUID

from wholoo.all_movies.models import AllMoviesModel
from wholoo.all_series.models import AllSeriesModel
from wholoo.genre.models import GenreModel
from wholoo.genres.models import GenresModel
from wholoo.movies.models import MoviesModel
from wholoo.season.models import Item, SeasonModel
from wholoo.tv.models import TVModel

from plugins.Hulu.constants import HuluMediaType


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://hulu.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str | UUID, media_type: HuluMediaType) -> str:
    return build_url(f"{media_type}/{title_key}")


# TODO: Validate
def episode_url(episode_key: str) -> str:
    return build_url(f"watch/{episode_key}")


# TODO: Validate
def image_url(path: str | None) -> str | None:
    if path is None:
        return None
    operations = quote('[{"resize":"1920x1920|max"},{"format":"webp"}]', safe=":,")
    return f"{path}&operations={operations}"


# TODO: Validate
def thumbnail_url(path: str | None) -> str | None:
    if path is None:
        return None
    operations = quote('[{"resize":"600x600|max"},{"format":"webp"}]', safe=":,")
    return f"{path}&operations={operations}"


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(key: str) -> tuple[str, int]:
    title_key, _, season_number = key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def season_numbers(series: TVModel) -> list[int]:
    numbers: dict[int, None] = {}
    for component in series.components:
        for item in component.items:
            grouping = item.series_grouping_metadata
            if grouping is not None:
                numbers[grouping.season_number] = None
    return list(numbers)


# TODO: Validate
def season_items(season: SeasonModel) -> list[Item]:
    items: dict[UUID, Item] = {}
    for item in season.items:
        items.setdefault(item.id, item)
    return list(items.values())


# TODO: Validate
def title_urls(page: AllSeriesModel | AllMoviesModel | GenreModel) -> list[str]:
    """Return all title URLs from the given page."""
    layout = page.props.page_props.layout
    return [
        build_url(item.href)
        for component in layout.components or []
        if component.type == "list_card"
        for item in component.items or []
        if item.href
    ]


# TODO: Validate
def genre_ids(page: GenresModel) -> list[str]:
    layout = page.props.page_props.layout
    return [
        item.href.removeprefix("/hub/")
        for component in layout.components or []
        if component.type == "list_card"
        for item in component.items or []
        if item.href
    ]


# TODO: Validate
def title_plan(page: TVModel | MoviesModel) -> tuple[str, bool] | None:
    vod_items = page.details.vod_items
    if vod_items is None:
        return None
    bundle = vod_items.focus.entity.bundle
    # I have no idea why but these specifically need whitelisting.
    is_subscription = bundle.package_id not in (1, 2, 33) and (
        bundle.network_name != "Sony"
    )
    return bundle.network_name, is_subscription
