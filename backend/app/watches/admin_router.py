# TODO: Validate


from fastapi import APIRouter, Depends

from app.auth.dependencies import (
    SessionDep,
    get_current_active_superuser,
)
from app.watches.schemas import (
    WatchRelinkResults,
)
from app.watches.services import (
    relink_detached_watches,
)

watches_router = APIRouter(
    prefix="/watches",
    tags=["watches"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@watches_router.post(
    "/relink",
)
def admin_relink_watches(session: SessionDep) -> WatchRelinkResults:
    """Point every watch left without an episode back at one."""
    return relink_detached_watches(session)


router = APIRouter()
router.include_router(watches_router)
