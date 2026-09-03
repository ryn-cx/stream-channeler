# TODO: Validate
from fastapi import APIRouter

from app.files.admin_router import router as admin_router

router = APIRouter()
router.include_router(admin_router)
