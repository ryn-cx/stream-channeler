# TODO: Validate
from fastapi import APIRouter

from app.unmatched_sources.admin_router import router as admin_router

router = APIRouter()
router.include_router(admin_router)
