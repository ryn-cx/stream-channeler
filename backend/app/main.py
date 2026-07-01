"""Stream Channeler application."""

from importlib import import_module

import sentry_sdk
from fastapi import APIRouter, FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.constants import APP_PATH


# TODO: Make this a private function upstream.
def _custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=_custom_generate_unique_id,
)


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# TODO: Enable this upstream.
app.add_middleware(GZipMiddleware)


# TODO: Implement this improved function upstream.
def automatically_import_routers() -> APIRouter:
    """Automatically import `router` from app/*/router.py."""
    api_router = APIRouter()
    for router_file in sorted(APP_PATH.glob("*/router.py")):
        module_name = router_file.parent.name

        if module_name == "private" and settings.ENVIRONMENT != "local":
            continue

        router = import_module(f"app.{module_name}.router").router
        api_router.include_router(router)

    return api_router


api_router = automatically_import_routers()

app.include_router(api_router, prefix=settings.API_V1_STR)
