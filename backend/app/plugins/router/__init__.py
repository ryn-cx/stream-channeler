# TODO: Validate
from fastapi import APIRouter

from app.plugins.admin_router import router as admin_router
from app.plugins.user_router import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(admin_router)
