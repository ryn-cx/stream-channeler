# TODO: Validate
from fastapi import APIRouter

from app.video_store.router.public import router as public_router

router = APIRouter()
router.include_router(public_router)
