# TODO: Validate
from fastapi import APIRouter

from app.comments.user_router import router as user_router

router = APIRouter()
router.include_router(user_router)
