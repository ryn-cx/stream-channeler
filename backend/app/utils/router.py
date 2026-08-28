# TODO: Validate
from fastapi import APIRouter

from app.utils.admin_router import router as admin_router
from app.utils.public_router import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)
