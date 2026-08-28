# TODO: Validate
from fastapi import APIRouter

from app.episodes.admin_router import router as admin_router
from app.episodes.public_router import router as public_router
from app.episodes.user_router import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(public_router)
router.include_router(admin_router)
