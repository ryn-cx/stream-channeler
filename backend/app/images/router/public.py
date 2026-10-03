# TODO: Validate
from pathlib import Path as FilePath

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.auth.dependencies import SessionDep
from app.episodes.dependencies import ExistingEpisode
from app.images import service
from app.images.service import ImageField
from app.seasons.dependencies import ExistingSeason
from app.titles.dependencies import ExistingTitle

images_router = APIRouter(prefix="/images", tags=["images"])


# TODO: Validate
def _image_response(cached_path: FilePath) -> FileResponse:
    return FileResponse(
        cached_path,
        media_type=f"image/{cached_path.suffix.removeprefix('.')}",
        headers={
            "Cache-Control": "public, max-age=31536000, s-maxage=31536000, immutable",
            "Access-Control-Allow-Origin": "*",
        },
    )


# TODO: Validate
@images_router.get(
    "/titles/{title_id}/{field}/{file_name}",  # noqa: FAST003
    response_class=FileResponse,
)
def get_title_image(
    session: SessionDep,
    title: ExistingTitle,
    field: ImageField,
) -> FileResponse:
    return _image_response(service.image_path(session, title, field))


# TODO: Validate
@images_router.get(
    "/seasons/{season_id}/{field}/{file_name}",  # noqa: FAST003
    response_class=FileResponse,
)
def get_season_image(
    session: SessionDep,
    season: ExistingSeason,
    field: ImageField,
) -> FileResponse:
    return _image_response(service.image_path(session, season, field))


# TODO: Validate
@images_router.get(
    "/episodes/{episode_id}/{field}/{file_name}",  # noqa: FAST003
    response_class=FileResponse,
)
def get_episode_image(
    session: SessionDep,
    episode: ExistingEpisode,
    field: ImageField,
) -> FileResponse:
    return _image_response(service.image_path(session, episode, field))


router = APIRouter()
router.include_router(images_router)
