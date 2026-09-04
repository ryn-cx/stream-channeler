# TODO: Validate
from fastapi import APIRouter

from app.sources.router.admin import router as admin_router

router = APIRouter()
router.include_router(admin_router)
