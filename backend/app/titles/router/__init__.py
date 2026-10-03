# TODO: Validate
from fastapi import APIRouter

from app.titles.router.admin import router as admin_router
from app.titles.router.public import router as public_router
from app.titles.router.user import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(public_router)
router.include_router(admin_router)
