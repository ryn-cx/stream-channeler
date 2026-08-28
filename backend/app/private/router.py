# TODO: Validate
from fastapi import APIRouter

from app.private.public_router import router as public_router

router = APIRouter()
router.include_router(public_router)
