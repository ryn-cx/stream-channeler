# TODO: Validate
"""What every other part of the plugin reads a title by."""

from collections.abc import Sequence
from urllib.parse import quote
from uuid import UUID

from wholoo.all_movies.models import AllMoviesModel
from wholoo.all_series.models import AllSeriesModel
from wholoo.genre.models import GenreModel
from wholoo.genres.models import GenresModel
from wholoo.movies.models import Component as MovieComponent
from wholoo.movies.models import Details as MovieDetails
from wholoo.movies.models import Item as MovieCollectionItem
from wholoo.season.models import Item, SeasonModel
from wholoo.tv.models import Component as SeriesComponent
from wholoo.tv.models import Details as TVDetails
from wholoo.tv.models import Item as SeriesCollectionItem
from wholoo.tv.models import TVModel

from plugins.Hulu.constants import (
    EPISODES_COLLECTION_IDS,
    HuluMediaType,
)


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://hulu.com/{path.lstrip('/')}"


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
    return [build_url(item.href) for item in page.items]


# TODO: Validate
def genre_ids(page: GenresModel) -> list[str]:
    return [item.href.removeprefix("/hub/") for item in page.items]


# TODO: Validate
def title_plan(details: TVDetails | MovieDetails) -> tuple[str, bool] | None:
    vod_items = details.vod_items
    if vod_items is None:
        return None
    bundle = vod_items.focus.entity.bundle
    # I have no idea why but these specifically need whitelisting.
    is_subscription = bundle.package_id not in (1, 2, 33) and (
        bundle.network_name != "Sony"
    )
    return bundle.network_name, is_subscription


# TODO: Validate
def collection_season_key(title_key: str, component_id: str) -> str:
    return f"{title_key}:collection-{component_id}"


# TODO: Validate
def is_collection_season_key(season_key: str) -> bool:
    return ":collection-" in season_key


# TODO: Validate
def split_collection_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, component_id = season_key.partition(":collection-")
    return title_key, component_id


# TODO: Validate
def title_item_url(
    item: SeriesCollectionItem | MovieCollectionItem,
) -> str | None:
    if item.field_type == HuluMediaType.SERIES:
        return build_url(f"{HuluMediaType.SERIES}/{item.id}")
    if item.field_type == HuluMediaType.MOVIE:
        return build_url(f"{HuluMediaType.MOVIE}/{item.id}")
    return None


# TODO: Validate
def watch_components(
    components: Sequence[SeriesComponent | MovieComponent],
) -> list[SeriesComponent | MovieComponent]:
    return [
        component
        for component in components
        if component.id not in EPISODES_COLLECTION_IDS
        and component.items
        and component.items[0].field_type in ("episode", "extra")
    ]


# TODO: Validate
def watch_component(
    components: Sequence[SeriesComponent | MovieComponent],
    component_id: str,
) -> SeriesComponent | MovieComponent:
    return next(
        component
        for component in watch_components(components)
        if component.id == component_id
    )


# TODO: Validate
def collection_urls(
    components: Sequence[SeriesComponent | MovieComponent],
) -> list[str]:
    urls: dict[str, None] = {}
    for component in components:
        if component.id in EPISODES_COLLECTION_IDS:
            continue
        for item in component.items:
            if url := title_item_url(item):
                urls[url] = None
    return list(urls)
