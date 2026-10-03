# TODO: Validate
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import sorted_plugins
from plugins.utils.proxy_client import proxy_client

type ImageField = Literal["image", "thumbnail", "poster", "poster_thumbnail"]


# TODO: Validate
def _kind(record: Title | Season | Episode) -> str:
    if isinstance(record, Title):
        return "titles"
    if isinstance(record, Season):
        return "seasons"
    return "episodes"


# TODO: Validate
def image_url(
    record: Title | Season | Episode,
    field: ImageField,
    plugin: type[AbstractPlugin],
) -> str | None:
    url: str | None = getattr(record, f"{field}_url", None)
    if url is None:
        return None
    file_name = plugin.image_file_name(url)
    return (
        f"{settings.API_V1_STR}/images/{_kind(record)}/{record.id}/{field}/{file_name}"
    )


# TODO: Validate
def _plugin_and_source_keys(
    session: Session,
    record: Title | Season | Episode,
) -> tuple[str, str]:
    statement = (
        select(Plugin.key, Source.key)
        .join(Source, col(Source.plugin_id) == col(Plugin.id))
        .join(Title, col(Title.source_id) == col(Source.id))
    )
    if isinstance(record, Title):
        statement = statement.where(col(Title.id) == record.id)
    else:
        statement = statement.join(Season, col(Season.title_id) == col(Title.id))
        if isinstance(record, Season):
            statement = statement.where(col(Season.id) == record.id)
        else:
            statement = statement.join(
                Episode,
                col(Episode.season_id) == col(Season.id),
            ).where(col(Episode.id) == record.id)
    plugin_key, source_key = session.exec(statement).one()
    return plugin_key, source_key


# TODO: Validate
def image_path(
    session: Session,
    record: Title | Season | Episode,
    field: ImageField,
) -> Path:
    plugin_key, source_key = _plugin_and_source_keys(session, record)
    plugin = next(
        (plugin for plugin in sorted_plugins() if plugin.plugin_name() == plugin_key),
        None,
    )
    url: str | None = getattr(record, f"{field}_url", None)
    if plugin is None or not plugin.PROXY_IMAGES or url is None:
        raise HTTPException(status_code=404, detail="Image not found")

    record_folder = (
        settings.IMAGE_CACHE_DIR / source_key / _kind(record) / str(record.id)
    )
    cached_path = record_folder / f"{field}-{plugin.image_file_name(url)}"
    if cached_path.exists():
        return cached_path

    image_format = cached_path.suffix.removeprefix(".")

    response = proxy_client().get(url, follow_redirects=True)
    response.raise_for_status()
    media_type = response.headers["content-type"].split(";")[0].strip()
    if media_type != f"image/{image_format}":
        raise HTTPException(
            status_code=502,
            detail=f"Upstream sent {media_type} instead of image/{image_format}",
        )

    record_folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=record_folder,
        prefix=f".{field}.",
        delete=False,
    ) as partial:
        partial.write(response.content)
    Path(partial.name).replace(cached_path)
    for stale_path in record_folder.glob(f"{field}[.-]*"):
        if stale_path != cached_path:
            stale_path.unlink(missing_ok=True)
    return cached_path
