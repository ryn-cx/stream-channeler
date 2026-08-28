# TODO: Validate
from fastapi import APIRouter

from app.users.admin_router import router as admin_router
from app.users.public_router import router as public_router
from app.users.user_router import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(public_router)
router.include_router(admin_router)
