# TODO: Validate


from fastapi import APIRouter

from app.plugins.schemas import PluginSupportInformation
from app.plugins.service import imports

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


# TODO: Validate
@plugins_router.get("/support-information")
def support_information() -> list[PluginSupportInformation]:
    return imports.support_information()


router = APIRouter()
router.include_router(plugins_router)
