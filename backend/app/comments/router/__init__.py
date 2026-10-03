# TODO: Validate
from fastapi import APIRouter

from app.comments.router.public import router as public_router
from app.comments.router.user import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(public_router)
