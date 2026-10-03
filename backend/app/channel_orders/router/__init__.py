# TODO: Validate
from fastapi import APIRouter

from app.channel_orders.router.admin import router as admin_router
from app.channel_orders.router.public import router as public_router
from app.channel_orders.router.user import router as user_router

router = APIRouter()
router.include_router(user_router)
router.include_router(public_router)
router.include_router(admin_router)
