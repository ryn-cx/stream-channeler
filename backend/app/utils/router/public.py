# TODO: Validate


from fastapi import APIRouter

utils_router = APIRouter(prefix="/utils", tags=["utils"])


# TODO: Validate
@utils_router.get("/health-check/")
async def health_check() -> bool:
    return True


router = APIRouter()
router.include_router(utils_router)
