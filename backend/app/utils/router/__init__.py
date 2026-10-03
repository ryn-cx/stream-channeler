# TODO: Validate
from fastapi import APIRouter

from app.utils.router.admin import router as admin_router
from app.utils.router.public import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)
