# TODO: Validate


from fastapi import APIRouter, Depends, status
from pydantic.networks import EmailStr

from app.auth.dependencies import get_current_active_superuser
from app.schemas import Message
from app.utils.service import generate_test_email, send_email

admin_router = APIRouter(
    prefix="/admin/utils",
    tags=["utils"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@admin_router.post("/test-email/", status_code=status.HTTP_201_CREATED)
def test_email(email_to: EmailStr) -> Message:
    """Test emails."""
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


router = APIRouter()
router.include_router(admin_router)
